"""配置管理 API"""

from fastapi import APIRouter, HTTPException
from web.routes import router
from web.models import ConfigOut, ConfigIn
from main import CONFIG_PATH


@router.get("/config", response_model=ConfigOut)
def get_config():
    if not CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="配置文件不存在")
    content = CONFIG_PATH.read_text(encoding="utf-8")
    return ConfigOut(content=content)


@router.put("/config", response_model=ConfigOut)
def update_config(req: ConfigIn):
    try:
        import yaml
        yaml.safe_load(req.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML 格式错误: {e}")
    CONFIG_PATH.write_text(req.content, encoding="utf-8")
    return ConfigOut(content=req.content)
