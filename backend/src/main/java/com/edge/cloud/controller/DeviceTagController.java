package com.edge.cloud.controller;

import com.edge.cloud.entity.DeviceTag;
import com.edge.cloud.repository.DeviceTagRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1")
public class DeviceTagController {

    private final DeviceTagRepository deviceTagRepository;

    public DeviceTagController(DeviceTagRepository deviceTagRepository) {
        this.deviceTagRepository = deviceTagRepository;
    }

    @PostMapping("/devices/{deviceId}/tags")
    public ResponseEntity<DeviceTag> addTag(
            @PathVariable String deviceId,
            @RequestBody Map<String, String> body) {
        DeviceTag tag = new DeviceTag();
        tag.setDeviceId(deviceId);
        tag.setTagKey(body.get("key"));
        tag.setTagValue(body.getOrDefault("value", ""));
        return ResponseEntity.ok(deviceTagRepository.save(tag));
    }

    @GetMapping("/devices/{deviceId}/tags")
    public ResponseEntity<List<DeviceTag>> getTags(@PathVariable String deviceId) {
        return ResponseEntity.ok(deviceTagRepository.findByDeviceId(deviceId));
    }

    @DeleteMapping("/devices/{deviceId}/tags/{tagKey}")
    @Transactional
    public ResponseEntity<Void> deleteTag(
            @PathVariable String deviceId,
            @PathVariable String tagKey) {
        deviceTagRepository.deleteByDeviceIdAndTagKey(deviceId, tagKey);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/devices/by-tag")
    public ResponseEntity<List<String>> findByTag(
            @RequestParam("key") String tagKey,
            @RequestParam("value") String tagValue) {
        List<String> deviceIds = deviceTagRepository
                .findByTagKeyAndTagValue(tagKey, tagValue)
                .stream()
                .map(DeviceTag::getDeviceId)
                .distinct()
                .toList();
        return ResponseEntity.ok(deviceIds);
    }
}
