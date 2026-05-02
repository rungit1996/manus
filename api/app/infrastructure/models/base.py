# 定义基础 ORM 类，让所有模型都继承这个类
from sqlalchemy.orm import declarative_base

Base = declarative_base()
