# coding:utf-8

"""翼型を扱うためのモジュール."""

import numpy as np
from scipy import interpolate

NUM_POINTS_FOR_MIX = 90
INTERP_METHOD_FOR_MIX = 'linear'


class Airfoil:
    """
    翼型を表現するクラス.

    Attributes
    ----------
    points : np.ndarray
        翼型上の点の列
    """

    def __init__(self, points=[], filepath=''):
        """
        初期化する.

        points か filepath のどちらかを与える

        Parameters
        ----------
        points : np.ndarray
            翼型上の点の列
        filepath : string
            datファイルのパス
        """
        if filepath != '':
            points = np.loadtxt(filepath, skiprows=1, delimiter=' ')

        self.points = points
        return

    def get_points(self, filter='all'):
        """
        翼型上の点を取得する.

        デフォルトで全周、filter引数で上面のみ、下面のみを取得できる

        Parameters
        ----------
        filter : string
            'all' -> 全周, 'upper' -> 上面のみ, 'lower' -> 下面のみ
        """
        if filter == 'all':
            return self.points
        elif filter == 'upper':
            idx_frontend = np.argmin(self.points[:, 0])
            return self.points[:idx_frontend+1]
        elif filter == 'lower':
            idx_frontend = np.argmin(self.points[:, 0])
            return self.points[idx_frontend:]


def mix(airfoil0, airfoil1, mix_ratio):
    """
    翼型を混合して新しいAirfoilインスタンスを作って返す.

    混合のための補間の間隔は NUM_POINTS_FOR_MIX で与える

    Parameters
    ----------
    airfoil0 : Airfoil
    airfoil1 : Airfoil
    mix_ratio : float
        混合比を指定する0から1までの小数
        0が与えられたら airfoil0 と等価な翼型を返す

    Return
    ------
    Airfoil
    """
    upper_points0 = airfoil0.get_points('upper')
    upper_points1 = airfoil1.get_points('upper')
    lower_points0 = airfoil0.get_points('lower')
    lower_points1 = airfoil1.get_points('lower')

    qx = np.linspace(0, 1, NUM_POINTS_FOR_MIX)
    interpolated = []
    raw = [upper_points0, upper_points1, lower_points0, lower_points1]
    for points in raw:
        interpolated.append(
            interpolate.interp1d(
                points[:, 0], points[:, 1],
                kind=INTERP_METHOD_FOR_MIX
            )(qx)
        )

    upper_y = interpolated[0]*mix_ratio + interpolated[1]*(1-mix_ratio)
    lower_y = interpolated[2]*mix_ratio + interpolated[3]*(1-mix_ratio)
    y = np.concatenate([upper_y[::-1], lower_y[1:]])
    x = np.concatenate([qx[::-1], qx[1:]])
    points = np.array([x, y]).T
    return Airfoil(points=points)
