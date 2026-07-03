/**
 * AI 能力配置中心
 * 新增能力：只在这里加一行，前端/后端自动适配
 */
export interface AbilityConfig {
  key: string
  name: string
  description: string
  /** 输入类型: text | image */
  inputType: 'text' | 'image'
  placeholder: string
  /** 支持的文件格式（仅 image 类型） */
  accept?: string
}

export const ABILITY_CONFIGS: Record<string, AbilityConfig> = {
  text_summary: {
    key: 'text_summary',
    name: '文本摘要',
    description: '提取长文本核心要点',
    inputType: 'text',
    placeholder: '输入要摘要的长文本...',
  },
  text_generation: {
    key: 'text_generation',
    name: '文本生成',
    description: '根据提示词生成内容',
    inputType: 'text',
    placeholder: '输入提示词...',
  },
  image_classify: {
    key: 'image_classify',
    name: '图像识别',
    description: '识别图片内容并分类',
    inputType: 'image',
    placeholder: '',
    accept: 'image/*',
  },
  image_generate: {
    key: 'image_generate',
    name: '图像生成',
    description: '根据文本生成图像',
    inputType: 'text',
    placeholder: '描述要生成的图像...',
  },
  code_generate: {
    key: 'code_generate',
    name: '代码生成',
    description: '需求→代码片段',
    inputType: 'text',
    placeholder: '描述需要的代码功能...',
  },
}

/** 根据后端 abilities API 返回的数据，合并本地配置 */
export function resolveAbility(key: string): AbilityConfig {
  return ABILITY_CONFIGS[key] || ABILITY_CONFIGS.text_summary
}
