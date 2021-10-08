# リブ図面作成ツール

DXF形式のリブ図面を作成するためのツール

## 使い方

1. `data/config/config.csv` に設定を記述する(書式は `sample_config.csv` 参照のこと)
2. `data/config/` 下にリブ情報のファイルを置く(ファイル名は`config.csv`と呼応させ、書式は`sample_ribdata.csv`に倣う)
3. `data/airfoils/` 下に翼型の`.dat`ファイルを置く(形式はXFLR5と同様とし、ファイル名はリブ情報のファイルに記述した翼型名と一致させる)
4. `codes/main.py` を実行する
5. `data/figure/` 下に`.dxf`ファイルが出力される

## 動作環境

開発は以下の環境で行なった

* Python
  * python 3.9.7
  * numpy 1.21.2
  * scipy 1.7.1
  
* AutoCAD
  * AutoCAD2020 Q.46.M.184
