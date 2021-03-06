#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File    : runner.py
# @Time    : 2021/5/20 15:30
# @Author  : Kelvin.Ye
import configparser
import getopt
import os
import sys
import time
import traceback
from datetime import datetime
from subprocess import PIPE, STDOUT, Popen


# 添加项目路径到path
sys.path.append(os.path.dirname(sys.path[0]))


# 配置文件路径
__CONFIG_PATH__ = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config.ini'))
if not os.path.exists(__CONFIG_PATH__):
    raise FileExistsError(f'配置文件不存在，路径:[ {__CONFIG_PATH__} ]')


# 配置对象
config = configparser.ConfigParser()
config.read(__CONFIG_PATH__)


# JMeterHome目录路径
__JMETER_HOME__ = config.get('jmeter', 'home')
# JMeterBin目录路径
__JMETER_BIN__ = os.path.abspath(os.path.join(__JMETER_HOME__, 'bin'))
# JMeterLog文件路径
__JMETER_LOG__ = os.path.abspath(os.path.join(__JMETER_BIN__, 'jmeter.log'))
# JMeterConfig目录路径
__JMETER_CONFIG__ = os.path.join(__JMETER_HOME__, 'config')
# JMeterReport目录路径
__JMETER_REPORT__ = os.path.join(__JMETER_HOME__, 'htmlreport')
# 默认执行脚本目录路径
__DEFAULT_SCRIPT_DIRECTORY__ = config.get('default', 'script.directory', fallback=None)


class JMeter:
    """JMeter类"""

    def __init__(self, env: str, reportname: str):
        self.jmeter_start = os.path.join(__JMETER_BIN__, 'jmeter')
        self.options = (f' -n -j "{__JMETER_LOG__}" -JconfigName="{env}" -JreportName="{reportname}" -JisAppend="true" -t ')

    def execute(self, scriptpath: str) -> None:
        """根据路径执行JMeter脚本"""
        print(f'开始执行脚本:[ {os.path.split(scriptpath)[1]} ]')
        command = self.jmeter_start + self.options + f'"{scriptpath}"'
        print(f'执行命令:[ {command} ]\n')

        popen = Popen(command, stdout=PIPE, stderr=STDOUT, shell=True, universal_newlines=True, encoding='utf-8')
        while popen.poll() is None:  # 检查子进程是否结束
            line = popen.stdout.readline()
            line = line.strip()
            if line:
                # 过滤没啥用的信息
                if line.startswith('Creating'):
                    continue
                if line.startswith('Created'):
                    continue
                if line.startswith('Starting'):
                    continue
                if line.startswith('Waiting'):
                    continue
                if line.startswith('summary'):
                    continue
                if line.startswith('Tidying'):
                    continue
                if line.endswith('end of run'):
                    continue
                print(line)

        if popen.returncode == 0:
            # execution success
            ...
        else:
            print('命令执行失败\n')


def run(env: str, dirpath: str, project: str) -> None:
    """批量运行JMeter

    Args:
        env (str): 环境名称
        dirpath (str): 脚本目录路径
        project (str): 项目名称，用于分类不同项目的测试报告存放路径

    """
    if not dirpath:
        raise ValueError('目录路径不能为空')

    if not os.path.exists(dirpath):
        raise FileNotFoundError(f'目录不存在，路径:[ {dirpath} ]')

    # 判断路径是目录还是脚本
    jmx_list = []
    if os.path.isdir(dirpath):
        jmx_list = get_script_list(dirpath)
    else:
        raise ValueError('仅支持批量运行，如需执行单个脚本，请直接使用JMeterGui运行')

    # 待执行脚本列表非空校验
    if not jmx_list:
        raise Exception(f'目录下不存在脚本，路径:[ {dirpath} ]')

    # 过滤含skip的脚本
    jmx_list = filter_skip_script(jmx_list)

    # 统计总脚本数
    script_total = len(jmx_list)

    # 设置当前工作路径为jmeter\bin
    os.chdir(__JMETER_BIN__)
    reportname = create_reportname()
    if project:
        reportname = os.path.join(project, reportname)
    jmeter = JMeter(env, reportname)

    job_starttime = current_strftime()
    print(f'开始时间:[ {job_starttime} ]')
    print(f'JMeter目录:[ {__JMETER_HOME__} ]')
    print(f'脚本目录:[ {dirpath} ]')
    print(f'脚本总数:[ {script_total} ]')
    print('脚本列表:')
    for index, script in enumerate(jmx_list):
        print(f'    {index + 1}. {script}')
    print('\n')

    # 用于统计完成脚本数
    completed_total = 0
    # 记录开始时间
    starttime = current_timestamp()

    for script in jmx_list:
        current_starttime = current_timestamp()
        jmeter.execute(script)
        current_elapsed_time = current_timestamp() - current_starttime
        completed_total += 1
        print(f'脚本耗时:[ {seconds_to_hms(current_elapsed_time)} ]\n')
        print(f'完成总数:[ {completed_total} ]')
        print(f'剩余总数:[ {script_total - completed_total} ]')
        print(f'执行总进度:[ {decimal_to_percentage(completed_total / script_total)} ]')

    # 统计总耗时
    total_elapsed_time = current_timestamp() - starttime
    print(f'任务总耗时:[ {seconds_to_hms(total_elapsed_time)} ]\n')

    # 输出报告路径
    reportpath = os.path.join(__JMETER_REPORT__, reportname)
    print(f'所有脚本执行完毕，详情请查看测试报告，报告路径:[ {reportpath} ]')

    # 添加环境变量
    # os.environ['reportPath'] = reportpath
    # os.environ['reportName'] = os.path.split(reportpath)[1]


def create_reportname():
    return 'inftest-report-' + datetime.now().strftime('%Y.%m.%d-%H.%M.%S') + '.html'


def filter_skip_script(jmx_list: list):
    return [jmx for jmx in jmx_list if 'skip' not in os.path.split(jmx)[1]]


def get_configfile_list():
    file_list = []
    for file in os.listdir(__JMETER_CONFIG__):
        if file.endswith('.yaml'):
            file_list.append(file)
    return file_list


def get_script_list(dirpath):
    """返回目录及子目录下所有的jmx脚本"""
    jmxs = []
    for parent, dirnames, filenames in os.walk(dirpath):
        for filename in filenames:
            if filename.endswith('.jmx'):
                jmxs.append(os.path.join(parent, filename))
    return jmxs


def current_timestamp():
    return int(time.time())


def current_strftime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def seconds_to_hms(seconds: int) -> str:
    """秒数转换为时分秒"""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return '%02dh:%02dm:%02ds' % (h, m, s)


def decimal_to_percentage(decimal: float) -> str:
    """小数转百分比"""
    return '%.2f%%' % (decimal * 100)


def get_args(argv):
    environment = None
    directory = None
    project = None

    try:
        opts, args = getopt.getopt(argv, 'he:d:p:', ['help', 'environment=', 'directory=', 'project='])
    except getopt.GetoptError:
        print('使用说明')
        print('runner.py -e <environment> -d <directory> -p <project>')
        print('runner.py --environment=<environment> --directory=<directory> --project=<project>')
        sys.exit()

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print('使用说明')
            print('runner.py -e <environment> -d <directory> -p <project>')
            print('runner.py --environment=<environment> --directory=<directory> --project=<project>')
            sys.exit()
        elif opt in ('-e', '--environment'):
            environment = arg
        elif opt in ('-d', '--directory'):
            directory = arg
        elif opt in ('-p', '--project'):
            project = arg

    return environment, directory, project


if __name__ == '__main__':
    try:
        configfile_list = get_configfile_list()
        environment, directory, project = get_args(sys.argv[1:])

        if not environment:
            print('environment配置名称不允许为空，请重试')
            sys.exit()

        if not environment.endswith('.yaml'):
            environment = environment + '.yaml'

        if environment not in configfile_list:
            print('environment配置名称不存在，请重试')
            sys.exit()

        if not directory and not __DEFAULT_SCRIPT_DIRECTORY__:
            print('directory脚本目录或默认脚本目录不允许为空，请重试')
            sys.exit()

        if directory:
            dirpath = directory
        else:
            dirpath = __DEFAULT_SCRIPT_DIRECTORY__

        run(environment, dirpath, project)
    except Exception:
        traceback.print_exc()
