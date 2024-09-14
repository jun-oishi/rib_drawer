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

DEFAULT_TEXTCOLOR = RED


def direct(dist, theta):
    """長さdist, 向きthetaのベクトルを返す."""
    return dist * np.array([np.cos(theta), np.sin(theta)])


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
