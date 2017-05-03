# coding:utf8
# luofuwen

import logging


class Config:
    # log config
    loggerConfig = {
        'logFile':'/tmp/workflow2_block.log',
        'logFmt':'%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s',
        'logLevel': logging.INFO,
        'logName': 'Workflow2XBlockLogger',
    }

    # 题库github配置
    getQuestionJsonUrl = 'https://api.github.com/repos/chyyuu/os_course_exercise_library/contents/data/json/%(qDir)d/%(qNo)d.json'

    # 保存学生回答记录的最大条数
    maxSizeOfAnswerList = 5

    # teacher/answer gitlab 配置
    teacherGitlab = {
        'root_token': 'xxxxxxxxxxxxxxxxxxxx',
        'hostname': '192.168.1.136',
        'port': 80,
        'repo_id': 287,
        'file_operation_url': '/api/v3/projects/%(repo_id)d/repository/files?private_token=%(root_token)s&&file_path=%(filepath)s&&ref=%(ref)s',
        'ref': 'master',
    }
