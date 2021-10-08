# coding:utf-8

"""DXFファイルを編集するためのモジュール."""

import numpy as np

"""
WPM の処理を参考にしている。
公式の最新版は以下を参照のこと
http://docs.autodesk.com/ACD/2011/JPN/filesDXF/WSfacf1429558a55de185c428100849a0ab7-5f35.htm
"""


def direct(dist, theta):
    """長さdist, 向きthetaのベクトルを返す."""
    return dist*np.array([np.cos(theta), np.sin(theta)])


def append_next_point(points, movement):
    """点列の末尾に最後の点をmovementだけ移動させた点を加える."""
    points = np.concatenate(
        [points, (points[-1]+movement).reshape((1, 2))],
        axis=0
    )
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


def offset(points, distance, direction='lefthand'):
    """
    ポリラインをオフセットした点列を返す.

    directionがlefthandなら点の並ぶ向きに向かって左側、righthandなら右側にずらす
    """
    offset_points = []

    # 最初の一点は特別
    theta = np.arctan2(
        points[1, 1]-points[0, 1], points[1, 0]-points[0, 0]
    ) + np.pi/2
    if direction == 'righthand':
        theta += np.pi
    offset_points.append(
        points[0]
        + distance*np.array([np.cos(theta), np.sin(theta)])
    )

    for i in range(1, len(points)-1):
        theta = np.arctan2(
            points[i+1, 1]-points[i-1, 1], points[i+1, 0]-points[i-1, 0]
        ) + np.pi/2
        if direction == 'righthand':
            theta = theta + np.pi
        offset_points.append(
            points[i]
            + distance*np.array([np.cos(theta), np.sin(theta)])
        )

    # 最後の一点は特別
    theta = np.arctan2(
        points[-1, 1]-points[-2, 1], points[-1, 0]-points[-2, 0]
    ) + np.pi/2
    if direction == 'righthand':
        theta += np.pi
    offset_points.append(
        points[-1]
        + distance*np.array([np.cos(theta), np.sin(theta)])
    )

    return np.array(offset_points)


def newfile(path):
    """新しいファイルを生成する."""
    file = DxfFile()
    file.setpath(path)
    file.addlines([
        '  0\n',
        'SECTION\n',
        '  2\n',
        'ENTITIES\n',
    ])
    return file


class DxfFile:
    """
    DXFファイルを表現するクラス.

    Attributes
    ----------
    __path : string
        ファイルのパス
    __lines : list of string
        ファイルの中身を行ごとに割ったもの
        各行の末尾に改行文字を含む
        末尾は必ず空行とする
    __is_saved : bool
        ファイルが保存済か(EOFが記述されているか)
    """

    def __init__(self):
        """中身を持たないファイルインスタンスを生成する."""
        self.__lines = []
        self.__is_saved = False
        return

    def addline(self, newline):
        """
        末尾に行を追加する.

        Parameters
        ----------
        newline : string

        Return
        ------
        True
            正常に完了したら
        """
        if self.is_saved():
            raise Exception('file already saved and not ready to edit')

        if newline[-1] != '\n':
            newline = newline + '\n'

        self.__lines.append(newline)

        return True

    def addlines(self, newlines):
        """
        末尾に複数行追加する.

        Parameters
        ----------
        newlines : list of string

        Return
        ------
        True
            正常に完了したら
        """
        for newline in newlines:
            self.addline(newline)
        return True

    def save(self):
        """
        ファイルを保存する.

        __lines に終了の合図を入れるので保存後は編集できない

        Return
        ------
        True
            正常に完了したら
        """
        self.addlines([
            '  0\n',
            'ENDSEC\n',
            '  0\n',
            'EOF\n'
        ])
        with open(self.getpath(), mode='w') as file:
            file.writelines(self.__lines)
        self.__is_saved = True
        return True

    def setpath(self, path):
        """ファイル名(保存先のパス)をセットする."""
        self.__path = path
        return True

    def getpath(self):
        """ファイルの保存場所を取得する."""
        return self.__path

    def is_saved(self):
        """ファイルが保存済か確認する."""
        return self.__is_saved

    def polyline(self, points):
        """
        ポリラインを描画する.

        Parameters
        ----------
        points : array of array of two floats
            ポリラインを定義する点の座標の配列

        Return
        ------
        True
            正常に完了したら
        """
        beginning_lines = [
            '  0\n',
            'POLYLINE\n',
            ' 8\n',
            '0\n',
            ' 6\n',
            'CONTINUOUS\n',
            ' 62\n',
            '7\n',
            ' 66\n',
            '1\n',
            ' 10\n',
            '0\n',
            ' 20\n',
            '0\n',
            ' 30\n',
            '0\n',
            ' 70\n',
            '128\n',
            ' 40\n',
            '1.0\n',
            ' 41\n',
            '1.0\n',
        ]
        ending_lines = [
            '  0\n',
            'SEQEND\n',
            ' 8\n',
            '0\n',
            ' 6\n',
            'CONTINUOUS\n',
            ' 62\n',
            '7\n',
        ]
        content = [
            [
                '  0\n',
                'VERTEX\n',
                ' 8\n',
                '0\n',
                ' 6\n',
                'CONTINUOUS\n',
                ' 62\n',
                '7\n',
                ' 10\n',
                f'{xy[0]}\n',
                ' 20\n',
                f'{xy[1]}\n',
                ' 30\n',
                '0\n',
                ' 40\n',
                '0\n',
                ' 41\n',
                '0\n'
            ]
            for xy in points
        ]

        self.addlines(beginning_lines)
        for content_lines in content:
            self.addlines(content_lines)
        self.addlines(ending_lines)
        return True

    def circle(self, pos_center, radius):
        """
        円を描画する.

        Parameters
        ----------
        pos_center : list of two floats
            中心の座標
        radius : float
            半径

        Return
        ------
        True
            正常に完了したら
        """
        lines = [
            '  0\n',
            'CIRCLE\n',
            ' 8\n',
            '0\n',
            ' 6\n',
            'CONTINUOUS\n',
            ' 62\n',
            '7\n',
            ' 10\n',
            f'{pos_center[0]}\n',
            ' 20\n',
            f'{pos_center[1]}\n',
            ' 30\n',
            '0\n',
            ' 40\n',
            f'{radius}\n',
        ]

        self.addlines(lines)

        return True
