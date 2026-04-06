    def _segment_cluster_classify(
        self,
        image: np.ndarray,
        classes_config: Dict[str, dict],
        merged_classes: Dict[str, dict],
        requested_classes: set,
        class_probs: Dict[str, float],
        threshold: float,
        min_area: float,
        orig_h: int,
        orig_w: int,
    ) -> Dict[str, SegmentResult]:
        """
        v4: 检出优先 + 严格防误检

        业务原则:
          1. 检出为主: 小面积高置信度即算检出，不追求 IOU 覆盖
          2. 避免误检: 异常类必须是簇 argmax 且置信度 > 0.5，必须高于正常水/背景
          3. 水体约束: 河道区域面积占比大，异常必须在水体内
        """
        import cv2
        from sklearn.cluster import KMeans

        # ━━━ 第 1 步: 图像级异常门控 ━━━
        img_anomaly_class = None
        img_anomaly_prob = 0.0
        for cls_name in requested_classes:
            prob = class_probs.get(cls_name, 0.0)
            if prob > img_anomaly_prob:
                img_anomaly_prob = prob
                img_anomaly_class = cls_name

        img_normal_prob = class_probs.get("_normal_water", 0.0)
        # 图像级没有任何异常类概率 > 0.15 → 直接返回空
        if img_anomaly_prob < 0.15:
            return {}

        # ━━━ 第 2 步: RADIO 特征提取 + 聚类 ━━━
        result = self.backbone.extract_features_numpy(image, self.input_size)
        H_patch, W_patch = result["grid_size"]

        adaptor_feats = result.get("adaptor_features")
        if adaptor_feats is None:
            adaptor_feats = result["features"]
        feats = adaptor_feats[0].float()

        n_clusters = max(8, min(16, int(np.sqrt(feats.shape[0]))))
        feats_np = feats.cpu().numpy()
        feats_norm = feats_np / (np.linalg.norm(feats_np, axis=1, keepdims=True) + 1e-8)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10, max_iter=100)
        labels = kmeans.fit_predict(feats_norm)

        # ━━━ 第 3 步: 簇级 SigLIP2 分类 ━━━
        cluster_results = []

        for cluster_id in range(n_clusters):
            cluster_patch = (labels == cluster_id)
            cluster_grid = cluster_patch.astype(np.float32).reshape(1, 1, H_patch, W_patch)
            cluster_up = F.interpolate(
                torch.from_numpy(cluster_grid), size=(orig_h, orig_w),
                mode="bilinear", align_corners=False,
            ).squeeze().numpy()
            cluster_binary = cluster_up > 0.5

            ys, xs = np.where(cluster_binary)
            if len(ys) == 0:
                continue

            pad = 5
            y1 = max(0, int(ys.min()) - pad)
            y2 = min(orig_h, int(ys.max()) + pad)
            x1 = max(0, int(xs.min()) - pad)
            x2 = min(orig_w, int(xs.max()) + pad)

            crop = image[y1:y2, x1:x2]
            if crop.shape[0] < 32 or crop.shape[1] < 32:
                continue

            crop_probs = self.classify(crop, merged_classes)
            top_class = max(crop_probs, key=crop_probs.get) if crop_probs else "_background"

            # 簇的最佳异常类
            best_anom_cls = None
            best_anom_prob = 0.0
            for cls_name in requested_classes:
                p = crop_probs.get(cls_name, 0.0)
                if p > best_anom_prob:
                    best_anom_prob = p
                    best_anom_cls = cls_name

            cluster_results.append({
                "id": cluster_id,
                "top_class": top_class,
                "crop_probs": crop_probs,
                "binary": cluster_binary,
                "patch": cluster_patch,
                "best_anom_cls": best_anom_cls,
                "best_anom_prob": best_anom_prob,
            })

        # ━━━ 第 4 步: 水体区域识别 ━━━
        # 水体 = _normal_water + 异常类 (排除 _background 天空/建筑/植被)
        water_mask = np.zeros((orig_h, orig_w), dtype=bool)
        for cr in cluster_results:
            top = cr["top_class"]
            is_water = (
                top in requested_classes or
                top == "_normal_water" or
                (not merged_classes.get(top, {}).get("is_background", False) and top != "_background")
            )
            if is_water:
                water_mask |= cr["binary"]

        # 水体面积检查: 河道区域应占图像 >= 15%
        water_ratio = float(water_mask.sum()) / water_mask.size
        if water_ratio < 0.15:
            return {}

        # ━━━ 第 5 步: 严格异常检测 (核心) ━━━
        # 只接受异常类为 argmax 且高置信度的簇
        anomaly_mask = np.zeros((orig_h, orig_w), dtype=bool)
        best_anomaly_class = None
        best_anomaly_score = 0.0
        all_patch_scores = np.zeros((H_patch, W_patch), dtype=np.float32)

        for cr in cluster_results:
            top_class = cr["top_class"]
            anom_cls = cr["best_anom_cls"]
            anom_prob = cr["best_anom_prob"]
            crop_probs = cr["crop_probs"]

            # 条件 1: 异常类必须是簇的 argmax (严格)
            if top_class not in requested_classes:
                continue

            # 条件 2: 异常置信度 > 0.5
            if anom_prob < 0.5:
                continue

            # 条件 3: 异常置信度必须高于 _normal_water
            normal_prob = crop_probs.get("_normal_water", 0.0)
            if anom_prob <= normal_prob:
                continue

            # 条件 4: 异常置信度必须高于所有背景类
            bg_prob = 0.0
            for cls_name, cls_cfg in merged_classes.items():
                if cls_cfg.get("is_background", False):
                    bg_prob = max(bg_prob, crop_probs.get(cls_name, 0.0))
            if anom_prob <= bg_prob:
                continue

            # 通过全部条件 → 确认异常簇
            anomaly_mask |= cr["binary"]
            all_patch_scores += (
                cr["patch"].reshape(H_patch, W_patch).astype(np.float32) * anom_prob
            )

            if anom_prob > best_anomaly_score:
                best_anomaly_score = anom_prob
                best_anomaly_class = anom_cls

        # ━━━ 第 6 步: 异常必须在水体内 ━━━
        anomaly_mask &= water_mask

        if not anomaly_mask.any():
            return {}

        # ━━━ 第 7 步: 轻量后处理 ━━━
        # 小核去噪 (3x3, 不去除有价值的检测区域)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        anomaly_mask = cv2.morphologyEx(
            anomaly_mask.astype(np.uint8), cv2.MORPH_OPEN, kernel
        ).astype(bool)

        # 保留 top-3 连通域
        if anomaly_mask.any():
            num_labels, labels_img, stats, _ = cv2.connectedComponentsWithStats(
                anomaly_mask.astype(np.uint8), connectivity=8
            )
            if num_labels > 2:
                areas = stats[1:, cv2.CC_STAT_AREA]
                top_n = min(3, len(areas))
                top_labels = set(np.argsort(areas)[-top_n:] + 1)
                anomaly_mask = np.isin(labels_img, list(top_labels))

        # 轻度平滑
        if anomaly_mask.any():
            mask_smooth = cv2.GaussianBlur(
                (anomaly_mask.astype(np.uint8) * 255), (5, 5), 0
            )
            mask_final = mask_smooth > 127
        else:
            mask_final = anomaly_mask

        area = float(mask_final.sum()) / mask_final.size
        # v4: 检出优先，面积阈值 0.5%
        if area < 0.005:
            return {}

        # ━━━ 第 8 步: 标签确定 ━━━
        if best_anomaly_class is None:
            if img_anomaly_prob > img_normal_prob:
                best_anomaly_class = img_anomaly_class
                best_anomaly_score = img_anomaly_prob
            else:
                return {}

        cfg = classes_config.get(best_anomaly_class, merged_classes.get(best_anomaly_class, {}))
        zh_name = cfg.get("zh", best_anomaly_class)

        return {
            best_anomaly_class: SegmentResult(
                class_name=best_anomaly_class,
                class_name_cn=zh_name,
                mask=mask_final,
                area_ratio=area,
                score=float(best_anomaly_score),
                patch_scores=all_patch_scores,
            )
        }

