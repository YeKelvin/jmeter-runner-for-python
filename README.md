# JMeter Runner For Python

批量执行JMeter脚本。

## 配置说明

使用前请先配置好config.ini文件

- jmeter.home: JMeter目录路径
- default.script.directory： 默认执行脚本目录路径

## 使用说明

```cmd
runner.py -h
runner.py --help
runner.py -e <environment> -d <directory>
runner.py --environment=<environment> --directory=<directory>
```
