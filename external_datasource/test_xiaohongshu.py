#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小红书关键词搜索测试
"""
import json
from xiaohongshu_client import XiaoHongShuClient


def test_keyword_search():
    """测试关键词搜索功能"""
    print("=" * 70)
    print("小红书关键词搜索测试")
    print("接口参数: keyword, keyword_relationship, start_time, end_time")
    print("=" * 70)
    
    client = XiaoHongShuClient()
    
    # 测试1: 中文逗号字符串
    print("\n【测试1】中文逗号分隔的字符串")
    print("-" * 70)
    try:
        result = client.keyword_search(
            keywords="冲锋衣，洗衣机",
            keyword_relationship="AND"
        )
        items = result.get('info_list', [])
        print(f"✓ 搜索成功")
        print(f"  关键词: '冲锋衣，洗衣机' (AND关系)")
        print(f"  返回结果数: {len(items)}")
        print(f"  结果: {json.dumps(items, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
    
    # 测试2: 英文逗号字符串
    print("\n【测试2】英文逗号分隔的字符串")
    print("-" * 70)
    try:
        result = client.keyword_search(
            keywords="冲锋衣,洗衣机",
            keyword_relationship="AND"
        )
        items = result.get('info_list', [])
        print(f"✓ 搜索成功")
        print(f"  关键词: '冲锋衣,洗衣机' (AND关系)")
        print(f"  返回结果数: {len(items)}")
        print(f"  结果: {json.dumps(items, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
    
    # 测试3: OR关系搜索
    print("\n【测试3】OR关系搜索")
    print("-" * 70)
    try:
        result = client.keyword_search(
            keywords="冲锋衣，洗衣机",
            keyword_relationship="OR"
        )
        items = result.get('info_list', [])
        print(f"✓ 搜索成功")
        print(f"  关键词: '冲锋衣，洗衣机' (OR关系)")
        print(f"  返回结果数: {len(items)}")
        print(f"  结果: {json.dumps(items, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")


if __name__ == "__main__":
    test_keyword_search()

