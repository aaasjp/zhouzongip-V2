#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小红书数据获取客户端
"""
import requests
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class XiaoHongShuClient:
    """小红书数据获取客户端"""
    
    def __init__(self, base_url: str = "http://150.139.129.134:8852"):
        """
        初始化小红书客户端
        
        Args:
            base_url: 小红书接口基础地址
        """
        self.base_url = base_url
        self.keyword_search_url = f"{base_url}/keyword_search"
        
    def keyword_search(
        self,
        keywords: List[str] or str,
        keyword_relationship: str = "AND",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        use_chinese_comma: bool = True
    ) -> Dict[str, Any]:
        """
        关键词搜索小红书内容
        
        Args:
            keywords: 关键词，可以是字符串（多个关键词用逗号分隔）或关键词列表
                     字符串示例: "海尔，空调" 或 "海尔,空调" (中英文逗号皆可)
                     列表示例: ["海尔", "空调"]
            keyword_relationship: 关键词关系，"AND" 或 "OR"，默认 "AND"
            start_time: 开始时间，10位时间戳字符串，可选
            end_time: 结束时间，10位时间戳字符串，可选
            use_chinese_comma: 当keywords为列表时，是否使用中文逗号连接，默认True
                              True: 使用"，"连接
                              False: 使用","连接
            
        Returns:
            Dict: 接口返回的数据
            
        Raises:
            requests.RequestException: 请求异常
            ValueError: 参数错误
        """
        # 参数验证
        if not keywords:
            raise ValueError("关键词不能为空")
            
        # 处理关键词
        if isinstance(keywords, list):
            # 列表转字符串，使用指定的逗号类型
            separator = "，" if use_chinese_comma else ","
            keyword_str = separator.join(keywords)
        else:
            # 字符串直接使用（支持中英文逗号）
            keyword_str = keywords
            
        # 验证关键词关系
        keyword_relationship = keyword_relationship.upper()
        if keyword_relationship not in ["AND", "OR"]:
            raise ValueError("keyword_relationship 必须是 'AND' 或 'OR'")
            
        # 构建请求参数（只有4个参数）
        params = {
            "keyword": keyword_str,
            "keyword_relationship": keyword_relationship
        }
        
        # 添加可选时间参数
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
            
        try:
            logger.info(f"发起小红书关键词搜索请求: {params}")
            
            # 发送POST请求
            response = requests.post(
                self.keyword_search_url,
                json=params,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应数据
            result = response.json()
            
            logger.info(f"小红书搜索成功，返回 {len(result.get('info_list', []))} 条结果")
            
            return result
            
        except requests.Timeout:
            logger.error("小红书接口请求超时")
            raise
        except requests.RequestException as e:
            logger.error(f"小红书接口请求失败: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"小红书接口响应解析失败: {str(e)}")
            raise
            
    def search_notes_by_keywords(
        self,
        keywords: List[str],
        max_results: int = 20,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        根据关键词搜索笔记，返回笔记列表
        
        Args:
            keywords: 关键词列表
            max_results: 最大返回结果数，默认20
            **kwargs: 其他参数，传递给 keyword_search 方法
            
        Returns:
            List[Dict]: 笔记列表
        """
        try:
            result = self.keyword_search(keywords, **kwargs)
            
            # 提取笔记数据（真实API返回的是 info_list）
            items = result.get("info_list", [])
            
            # 限制返回数量
            return items[:max_results]
            
        except Exception as e:
            logger.error(f"搜索笔记失败: {str(e)}")
            return []
            
    def search_by_time_range(
        self,
        keywords: List[str] or str,
        days: int = 7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        搜索指定天数内的内容
        
        Args:
            keywords: 关键词
            days: 搜索最近几天的内容，默认7天
            **kwargs: 其他参数
            
        Returns:
            Dict: 搜索结果
        """
        from datetime import datetime, timedelta
        
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # 转换为时间戳字符串
        start_timestamp = str(int(start_time.timestamp()))
        end_timestamp = str(int(end_time.timestamp()))
        
        return self.keyword_search(
            keywords,
            start_time=start_timestamp,
            end_time=end_timestamp,
            **kwargs
        )
        
    def extract_note_info(self, note: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取笔记的关键信息
        
        Args:
            note: 笔记原始数据（info_list中的一项）
            
        Returns:
            Dict: 提取的关键信息
        """
        try:
            # 真实API结构：笔记数据在 data 字段下
            data = note.get("data", {})
            
            info = {
                "id": note.get("id", ""),
                "uuid": data.get("uuid", ""),
                "mid": data.get("mid", ""),
                "title": data.get("title", ""),
                "content": data.get("content", ""),
                "url": data.get("url", ""),
                "wtype": data.get("wtype", ""),
                "ctime": data.get("ctime", ""),
                "utime": data.get("utime", ""),
                "surface_img": data.get("surface_img", ""),
                "pic_urls": data.get("pic_urls", []),
                "user": {
                    "uid": data.get("user", {}).get("uid", ""),
                    "name": data.get("user", {}).get("name", ""),
                    "gender": data.get("user", {}).get("gender", ""),
                    "province": data.get("user", {}).get("province", ""),
                    "city": data.get("user", {}).get("city", ""),
                    "ip_region": data.get("user", {}).get("ip_region", []),
                    "description": data.get("user", {}).get("description", ""),
                    "followers_count": data.get("user", {}).get("followers_count", 0),
                    "friends_count": data.get("user", {}).get("friends_count", 0),
                },
                "publisher": data.get("publisher", {}),
                "gather": data.get("gather", {}),
                "analysis": data.get("analysis", {}),
                "highlight": note.get("highlight", {}),
            }
                
            return info
            
        except Exception as e:
            logger.error(f"提取笔记信息失败: {str(e)}")
            return {}


# 便捷函数
def search_xiaohongshu(
    keywords: List[str] or str,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    便捷搜索函数
    
    Args:
        keywords: 关键词
        **kwargs: 其他参数
        
    Returns:
        List[Dict]: 笔记列表
    """
    client = XiaoHongShuClient()
    return client.search_notes_by_keywords(keywords, **kwargs)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 创建客户端
    client = XiaoHongShuClient()
    
    # 测试搜索
    try:
        result = client.keyword_search(
            keywords=["海尔", "空调"],
            keyword_relationship="AND",
            sort_type="general",
            page=1
        )
        print(f"搜索成功，返回结果: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}...")
        
        # 提取笔记信息
        items = result.get("info_list", [])
        if items:
            first_note = items[0]
            note_info = client.extract_note_info(first_note)
            print(f"\n第一条笔记信息: {json.dumps(note_info, ensure_ascii=False, indent=2)}")
            
    except Exception as e:
        print(f"测试失败: {str(e)}")

