# jpxtime
Japan Exchange Delivatives(Index) trading schedule and trading hours

## Installation

```bash
pip install jpxtime
```

## Examples
```python
from datetime import datetime
import jpxtime

# 取引時間中の場合は1が返る
jpxtime.is_open(datetime(2016, 1, 5, 10, 0))
```
```
1
```
```python
# 取引時間外の場合は0が返る
jpxtime.is_open(datetime(2016, 1, 5, 8, 0))
```
```
0
```
```python
# クロージングオークションの場合は2が返る
jpxtime.is_open(datetime(2016, 1, 5, 15, 10))
```
```
2
```
```python
# 年月をタプルで指定してSQ日を取得
jpxtime.get_sq((2016, 1))
```
```
datetime.date(2016, 1, 8)
```
```python
# 年月をintで指定してSQ日を取得
jpxtime.get_sq((201601))
```
```
datetime.date(2016, 1, 8)
```
```python
# 年月をstrで指定してSQ日を取得
jpxtime.get_sq('201601')
```
```
datetime.date(2016, 1, 8)
```
```python
# 2016/1/1 0:00から2016年1月限のSQ日までの期間を取得(年換算)
jpxtime.get_t(datetime(2016, 1, 1), jpxtime.get_sq((2016, 1)))
```
```
0.020205479452054795
```
