"""配置管理 API"""

from fastapi import HTTPException
from web.routes import router
from web.models import ConfigOut, ConfigIn
from core.config import CONFIG_PATH
import re


@router.get("/config", response_model=ConfigOut)
def get_config():
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="配置文件不存在")
    content = CONFIG_PATH.read_text(encoding="utf-8")
    content = re.sub(
        r'(?m)^(\s*api_key\s*:\s*).+$',
        r'\1"${OPENAI_API_KEY}"',
        content,
    )
    return ConfigOut(content=content)


@router.put("/config", response_model=ConfigOut)
def update_config(req: ConfigIn):
    try:
        import yaml
        parsed = yaml.safe_load(req.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML 格式错误: {e}")
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="配置根节点必须是对象")
    for section in ("ai", "output", "runtime"):
        if not isinstance(parsed.get(section), dict):
            raise HTTPException(status_code=400, detail=f"缺少配置对象: {section}")
    api_key = str(parsed["ai"].get("api_key", ""))
    if api_key and not (api_key.startswith("${") and api_key.endswith("}")):
        raise HTTPException(status_code=400, detail="禁止在配置文件中保存明文 API Key")
    if not str(parsed["ai"].get("base_url", "")).startswith("https://"):
        raise HTTPException(status_code=400, detail="ai.base_url 必须使用 HTTPS")

    temp_path = CONFIG_PATH.with_suffix(".yaml.tmp")
    temp_path.write_text(req.content, encoding="utf-8")
    temp_path.replace(CONFIG_PATH)
    return ConfigOut(content=req.content)
