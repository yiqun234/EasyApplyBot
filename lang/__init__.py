#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Language package initialization
"""

import os
import importlib

# 可用的语言包列表
AVAILABLE_LANGUAGES = {
    'zh_CN': '简体中文',
    'en_US': 'English (US)'
}

# 默认语言
DEFAULT_LANGUAGE = 'en_US'

def load_language(lang_code):
    """
    加载指定的语言包
    
    Args:
        lang_code: 语言代码，如 'zh_CN', 'en_US'
        
    Returns:
        语言包字典，如果语言包不存在则返回默认语言包
    """
    if lang_code not in AVAILABLE_LANGUAGES:
        lang_code = DEFAULT_LANGUAGE
        
    try:
        lang_module = importlib.import_module(f'lang.{lang_code}')
        return lang_module.TEXTS
    except (ImportError, AttributeError):
        # 如果找不到指定的语言包，尝试加载默认语言包
        try:
            lang_module = importlib.import_module(f'lang.{DEFAULT_LANGUAGE}')
            return lang_module.TEXTS
        except (ImportError, AttributeError):
            # 如果默认语言包也加载失败，返回空字典
            return {} 