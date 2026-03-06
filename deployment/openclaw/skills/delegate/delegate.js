/**
 * 智能委托系统 - 自动判断是否使用子代理
 *
 * 核心功能：自动分析任务复杂度，决定执行方式
 */

// 高权重关键词（每个+3分）
const HIGH_PRIORITY_KEYWORDS = [
  '全面', '完整', '所有', '深度', '详细',
  '修订', '优化', '重构', '分析', '研究',
  '批量', '多个', '所有文件',
  // English equivalents
  'comprehensive', 'complete', 'all', 'deep', 'detailed',
  'revise', 'optimize', 'refactor', 'analyze', 'research',
  'batch', 'multiple', 'all files'
];

// 中权重关键词（每个+2分）
const MEDIUM_PRIORITY_KEYWORDS = [
  '配置', '集成', '结合',
  '生成', '输出', '报告',
  // English equivalents
  'configure', 'integrate', 'combine',
  'generate', 'output', 'report'
];

// 复杂任务类型
const COMPLEX_TASK_TYPES = [
  '论文修订', '论文写作', 'paper revision', 'paper writing',
  '代码审查', '代码重构', 'code review', 'code refactoring',
  '批量处理', 'batch processing',
  '深度分析', '深度研究', 'deep analysis', 'deep research'
];

/**
 * 分析任务复杂度
 * @param {string} task - 任务描述
 * @returns {Object} 分析结果
 */
function analyzeTaskComplexity(task) {
  let score = 0;
  const reasons = [];

  // 1. 关键词检测
  for (const keyword of HIGH_PRIORITY_KEYWORDS) {
    if (task.includes(keyword)) {
      score += 3;
      reasons.push(`检测到高权重关键词: "${keyword}"`);
    }
  }

  for (const keyword of MEDIUM_PRIORITY_KEYWORDS) {
    if (task.includes(keyword)) {
      score += 2;
      reasons.push(`检测到中权重关键词: "${keyword}"`);
    }
  }

  // 2. 文件操作检测
  const fileMatches = task.match(/文件|脚本|代码|\.py|\.json|\.md|\.txt/gi);
  if (fileMatches) {
    const fileCount = fileMatches.length;
    score += Math.min(fileCount * 2, 10); // 最多加10分
    if (fileCount >= 3) {
      reasons.push(`检测到${fileCount}个文件相关操作`);
    }
  }

  // 3. 工具调用预估（基于动作词）
  const actionWords = task.match(/读取|写入|修改|分析|配置|执行|运行|检查|测试/g);
  if (actionWords) {
    score += actionWords.length;
    if (actionWords.length >= 5) {
      reasons.push(`预估需要${actionWords.length}+次工具调用`);
    }
  }

  // 4. 任务类型检测
  for (const taskType of COMPLEX_TASK_TYPES) {
    if (task.includes(taskType)) {
      score += 3;
      reasons.push(`检测到复杂任务类型: ${taskType}`);
      break;
    }
  }

  // 5. 长度检测（长任务通常更复杂）
  if (task.length > 200) {
    score += 2;
    reasons.push('任务描述较长，可能包含多个步骤');
  }

  // 计算预估时间（分钟）
  const estimatedTime = Math.min(Math.max(score * 2, 5), 60);

  return {
    score,
    reasons,
    needsSubagent: score >= 5, // 阈值：5分
    estimatedTime,
    suggestedModel: score >= 10 ? 'zai/glm-4.7' : 'zai/glm-4.7-flash',
    suggestedTimeout: estimatedTime * 60
  };
}

/**
 * 生成子代理任务描述
 * @param {string} originalTask - 原始任务
 * @param {Object} analysis - 分析结果
 * @returns {string} 增强后的任务描述
 */
function enhanceTaskDescription(originalTask, analysis) {
  return `任务：${originalTask}

执行要求：
- 分步骤执行，每完成一个任务输出进度
- 保持主对话清洁，只输出最终结果摘要
- 遇到问题时给出具体建议而非直接修改代码
- 使用子代理模式处理所有子任务
- 预计执行时间：${analysis.estimatedTime}分钟

请开始执行，并在每个主要步骤完成后报告进度。`;
}

/**
 * 生成子代理命令
 * @param {string} task - 任务描述
 * @param {Object} options - 选项
 * @returns {Object} 命令和分析结果
 */
function generateSubagentCommand(task, options = {}) {
  const analysis = analyzeTaskComplexity(task);
  const enhancedTask = enhanceTaskDescription(task, analysis);
  const model = options.model || analysis.suggestedModel;
  const timeout = options.timeout || analysis.suggestedTimeout;

  return {
    shouldDelegate: true,
    command: `/subagents spawn main "${enhancedTask}" --model ${model} --runTimeoutSeconds ${timeout}`,
    analysis,
    taskInfo: {
      originalTask: task,
      enhancedTask: enhancedTask,
      model: model,
      timeout: timeout
    }
  };
}

/**
 * 主处理函数 - 自动判断是否委托
 * @param {string} userInput - 用户输入
 * @param {Object} options - 选项
 * @returns {Object} 处理结果
 */
function handleUserTask(userInput, options = {}) {
  // 分析任务复杂度
  const analysis = analyzeTaskComplexity(userInput);

  // 如果不需要委托
  if (!analysis.needsSubagent) {
    return {
      shouldDelegate: false,
      reason: '任务简单，可在主对话中直接执行',
      analysis: analysis,
      recommendation: '直接执行'
    };
  }

  // 需要委托，生成命令
  return generateSubagentCommand(userInput, options);
}

/**
 * 格式化分析结果供用户查看
 * @param {Object} analysis - 分析结果
 * @returns {string} 格式化的字符串
 */
function formatAnalysisResult(analysis) {
  let result = `任务复杂度评分：${analysis.score}分\n`;
  result += `判断依据：\n`;

  for (const reason of analysis.reasons) {
    result += `  - ${reason}\n`;
  }

  result += `预估执行时间：${analysis.estimatedTime}分钟\n`;
  result += `建议模型：${analysis.suggestedModel}\n`;
  result += `决策：${analysis.needsSubagent ? '使用子代理' : '主对话执行'}`;

  return result;
}

// 导出函数
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    analyzeTaskComplexity,
    enhanceTaskDescription,
    generateSubagentCommand,
    handleUserTask,
    formatAnalysisResult,
    HIGH_PRIORITY_KEYWORDS,
    MEDIUM_PRIORITY_KEYWORDS,
    COMPLEX_TASK_TYPES
  };
}
