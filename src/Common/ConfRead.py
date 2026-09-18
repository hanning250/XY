# -*- coding: utf-8 -*-
# @Time : 2023/9/13 18:39
# @Author : qiu jiahang

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from src.Common import glo

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONF_PATH = PROJECT_ROOT / "resources" / "conf" / "isupConf.json"


def getConfJson():
    jsonStr = ''
    with open(CONF_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if (line.strip().startswith("//")):
                continue
            else:
                jsonStr += line
        content = json.loads(jsonStr)
        # print(content)
    return content

def loadJsonConfToGlobal(jsonStr):
    preserved_handler = glo.get_value('alarm_event_handler')
    glo._init()
    for section in ('ss', 'cms', 'ams', 'sms'):
        for key, value in jsonStr[section].items():
            glo.set_value(key, value)
    glo.set_value("ISUPKey", jsonStr["ISUPKey"])
    glo.set_value("PreviewDeviceID", jsonStr.get("PreviewDeviceID", ""))
    glo.set_value("PlaybackDeviceID", jsonStr.get("PlaybackDeviceID", ""))
    glo.set_value("CmsDeviceID", jsonStr.get("CmsDeviceID", ""))
    glo.init_runtime_state()
    if preserved_handler is not None:
        glo.set_value('alarm_event_handler', preserved_handler)

def get_req_body_from_template(template_path, parameters):
    # 解析 XML 文件
    tree = ET.parse(template_path)
    root = tree.getroot()

    # 注册命名空间，防止 ns0 前缀
    ET.register_namespace('', 'http://www.isapi.org/ver20/XMLSchema')

    # 遍历所有元素，检查文本中是否有占位符需要替换
    for elem in root.iter():
        if elem.text and isinstance(elem.text, str):  # 检查元素是否有文本
            for key, value in parameters.items():
                # 查找并替换占位符 ${key}
                if f"${{{key}}}" in elem.text:
                    elem.text = elem.text.replace(f"${{{key}}}", value)

    # 返回修改后的 XML 字符串
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)



if __name__ == '__main__':
    loadJsonConfToGlobal(getConfJson())
