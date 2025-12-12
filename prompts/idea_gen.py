# -*- coding: utf-8 -*-
"""
idea_gen.py 生成idea的prompt    
"""

idea_gen_prompt = """
# 创意生成主题：{theme}

# 创意生成要求

## 输出要求
输出三个视频创意，每个创意需包含拍摄思路、拍摄手法和吸引点说明。

## 创意标准
1. **视觉冲击力**：抓住用户眼球，吸引用户关注
2. **品牌优势**：凸显海尔品牌技术优势和产品特色
3. **角色契合**：符合周总理工男的技术专家形象和性格特点

## 创意方向
从传统方式升级，融入以下元素：
- **参与感**：增强用户互动和参与体验
- **玩家感**：营造趣味性和游戏化体验
- **埋梗**：巧妙植入话题点和记忆点
- **高端感**：体现品牌专业性和品质感
- **可酷可玩可晒**：具备社交传播价值，适合分享

## 目标受众
主要面向年轻用户和小红书群体，创意需新颖创新，符合年轻人审美和兴趣点。

## 输出要求
仅输出创意方案（包含拍摄思路、手法、亮点），不输出分镜脚本。
输出格式：[IDEA_START][TITLE_START]标题1[TITLE_END][CONTENT_START]创意方案1[CONTENT_END][IDEA_END][IDEA_START][TITLE_START]标题2[TITLE_END][CONTENT_START]创意方案2[CONTENT_END][IDEA_END][IDEA_START][TITLE_START]标题3[TITLE_END][CONTENT_START]创意方案3[CONTENT_END][IDEA_END]

"""