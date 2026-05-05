from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import RawNovelSignal


class BaseCollector(ABC):
    """采集器基类"""
    
    @abstractmethod
    def collect(self) -> list[RawNovelSignal]:
        """采集数据，返回原始信号列表"""
        ...
    
    @property
    @abstractmethod
    def name(self) -> str:
        """采集器名称"""
        ...
    
    @property
    @abstractmethod
    def source(self) -> str:
        """数据源标识"""
        ...
