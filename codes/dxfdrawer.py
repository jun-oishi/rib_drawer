# coding:utf-8

"""DXFファイルを編集するためのモジュール."""

import numpy as np
import ezdxf
from ezdxf.colors import (
    BYBLOCK,
    BYLAYER,
    BYOBJECT,
    RED,
    YELLOW,
    GREEN,
    CYAN,
    BLUE,
    MAGENTA,
    BLACK,
    WHITE,
    GRAY,
    LIGHT_GRAY,
)
from ezdxf.enums import TextEntityAlignment as TextAlign

from typing import Iterable, Union

DEFAULT_TEXTCOLOR = RED


class Vec2:
    def __init__(self, x: float, y: float):
        self.__x = x
        self.__y = y

    @property
    def x(self) -> float:
        return self.__x

    @property
    def y(self) -> float:
        return self.__y

    @x.setter
    def x(self, x: float):
        self.__x = float(x)

    @y.setter
    def y(self, y: float):
        self.__y = float(y)

    def __getitem__(self, index: int) -> float:
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        else:
            raise IndexError("index 0, 1 are only available")

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __mul__(self, other: float) -> "Vec2":
        return Vec2(self.x * other, self.y * other)

    def __rmul__(self, other: float) -> "Vec2":
        return self.__mul__(other)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return self.__add__(other * -1)

    def __truediv__(self, other: float) -> "Vec2":
        return self.__mul__(1 / other)

    def dot(self, other: "Vec2") -> float:
        return self.x * other.x + self.y * other.y

    def rotate_rad(self, angle: float) -> "Vec2":
        return Vec2(
            self.x * np.cos(angle) - self.y * np.sin(angle),
            self.x * np.sin(angle) + self.y * np.cos(angle),
        )

    def rotate_deg(self, angle: float) -> "Vec2":
        return self.rotate_rad(np.deg2rad(angle))

    @property
    def norm(self) -> float:
        return np.sqrt(self.dot(self))

    @property
    def theta(self) -> float:
        return np.arctan2(self.y, self.x)

    @property
    def theta_deg(self) -> float:
        return np.rad2deg(self.theta)

    @property
    def unit(self) -> "Vec2":
        return self / self.norm

    def distance(self, other: "Vec2") -> float:
        return (self - other).norm

    def angle_between_rad(self, other: "Vec2") -> float:
        return np.arccos(self.dot(other) / (self.norm * other.norm))

    def angle_between_deg(self, other: "Vec2") -> float:
        return np.rad2deg(self.angle_between_rad(other))


class Vec2Arr(list):
    def __init__(self, arr: np.ndarray | Iterable[Vec2]):
        if isinstance(arr, np.ndarray):
            if arr.shape[1] != 2:
                raise ValueError("arr must be a 2D array")
            super().__init__([Vec2(x, y) for x, y in arr])
        elif isinstance(arr, Iterable) and all([isinstance(v, Vec2) for v in arr]):
            super().__init__(arr)
        else:
            TypeError("arr must be a 2D array or an iterable of Vec2")

    def __getitem__(self, index: int) -> Vec2:
        return super().__getitem__(index)

    def append(self, vec: Vec2):
        if not isinstance(vec, Vec2):
            raise TypeError("vec must be a Vec2")
        super().append(vec)

    def append_tail(self, vec: Vec2):
        self.append(self[-1] + vec)

    def offset(self, distance: float, *, direction: str = "lefthand") -> "Vec2Arr":
        """offset all points by distance"""
        angle = np.pi / 2 if direction == "lefthand" else -np.pi / 2
        ret = []
        for i in range(len(self)):
            j = max(i - 1, 0)
            k = min(i + 1, len(self) - 1)
            ret.append(self[i] + (self[k] - self[j]).unit.rotate_rad(angle) * distance)
        return Vec2Arr(ret)


def direct(dist, theta) -> tuple[float, float]:
    """長さdist, 向きthetaのベクトルを返す."""
    return tuple(dist * np.array([np.cos(theta), np.sin(theta)]))


def append_next_point(points, movement):
    """点列の末尾に最後の点をmovementだけ移動させた点を加える."""
    points = np.concatenate([points, (points[-1] + movement).reshape((1, 2))], axis=0)
    return points


def divide(points, ratio):
    """
    pointsが両端を表す線分をratioで内分する点を求める.

    ratio=0の時points[0]、ratio=1の時points[1]そのものを返す

    Return
    ------
    np.ndarray
    """
    d = np.array(points[1]) - np.array(points[0])
    return points[0] + ratio * d


def offset(points, distance, direction="lefthand"):
    """
    ポリラインをオフセットした点列を返す.

    directionがlefthandなら点の並ぶ向きに向かって左側、righthandなら右側にずらす
    """
    offset_points = []

    # 最初の一点は特別
    theta = (
        np.arctan2(points[1, 1] - points[0, 1], points[1, 0] - points[0, 0]) + np.pi / 2
    )
    if direction == "righthand":
        theta += np.pi
    offset_points.append(
        points[0] + distance * np.array([np.cos(theta), np.sin(theta)])
    )

    for i in range(1, len(points) - 1):
        theta = (
            np.arctan2(
                points[i + 1, 1] - points[i - 1, 1], points[i + 1, 0] - points[i - 1, 0]
            )
            + np.pi / 2
        )
        if direction == "righthand":
            theta = theta + np.pi
        offset_points.append(
            points[i] + distance * np.array([np.cos(theta), np.sin(theta)])
        )

    # 最後の一点は特別
    theta = (
        np.arctan2(points[-1, 1] - points[-2, 1], points[-1, 0] - points[-2, 0])
        + np.pi / 2
    )
    if direction == "righthand":
        theta += np.pi
    offset_points.append(
        points[-1] + distance * np.array([np.cos(theta), np.sin(theta)])
    )

    return np.array(offset_points)


def newfile(path) -> "DxfFile":
    """新しいファイルを生成する."""
    return DxfFile.new(path)


class DxfFile:
    """
    DXFファイルを表現するクラス.

    Attributes
    ----------
    __path : string
        ファイルのパス
    """

    def __init__(self, path: str = ""):
        """中身を持たないファイルインスタンスを生成する."""
        self.__drawing = ezdxf.new(setup=True)
        self.__msp = self.__drawing.modelspace()
        self.__path = path
        return

    @classmethod
    def new(cls, path: str) -> "DxfFile":
        return cls(path)

    def save(self):
        """
        ファイルを保存する.
        """
        self.__drawing.saveas(self.__path)
        return True

    def polyline(self, points):
        """
        ポリラインを描画する.

        Parameters
        ----------
        points : array of array of two floats
            ポリラインを定義する点の座標の配列
        """
        self.__msp.add_lwpolyline(points)

    def circle(self, pos_center, radius):
        """
        円を描画する.

        Parameters
        ----------
        pos_center : list of two floats
            中心の座標
        radius : float
            半径
        """
        self.__msp.add_circle(pos_center, radius)

    def text(
        self, content: str, pos: np.ndarray = np.array([0, 0]), rotation_deg: float = 0
    ):
        self.__msp.add_text(
            content,
            height=10,
            rotation=rotation_deg,
            dxfattribs={"color": DEFAULT_TEXTCOLOR},
        ).set_placement(pos, align=TextAlign.LEFT)
