# coding: utf8
# luofuwen
import pkg_resources

from xblock.core import XBlock
from xblock.fields import Scope, Integer, Dict, List, Boolean, String
from xblock.fragment import Fragment
from conf import Config
from util import Util
from GitRepo import GitRepo
import json
import hashlib
import logging
import datetime
import urllib2
import base64


class Test(object):
    pass


class Workflow2XBlock(XBlock):
    """
    这是学生回答习题的，需要保存每个学生的回答状态
    """

    logger = Util.logger(Config.loggerConfig)
    gitlabRepo = GitRepo(dict(Config.teacherGitlab, **{'logger': logger}))

    # 这是xblock 的特殊fields 用于指定xblock的名字
    display_name = String(display_name='Display Name', default=u'练习题工作流', scope=Scope.settings, help='Name of the component in the edxplatform')

    # 学生能够回答该问题的最大尝试次数,0表示无限制
    # 注意：下面的字段定义的Scope为user_state_summary，这样的设置让openedx允许从LMS修改这些字段
    #       处于安全性的考虑，我个人不建议这样的修改，但是老师一定需要这样的功能。
    maxTry = Integer(default=0, scope=Scope.content)
    #maxTry = Integer(default=0, scope=Scope.user_state_summary)
    # 当前block保存的题目
    questionJson = Dict(default={}, scope=Scope.content)
    #questionJson = Dict(default={}, scope=Scope.user_state_summary)
    # 当前block保存的题题号
    qNo = Integer(default=0, scope=Scope.content)
    #qNo = Integer(default=0, scope=Scope.user_state_summary)
    # 学生当前已经尝试的次数
    tried = Integer(default=0, scope=Scope.user_state)
    # 学生每次回答的记录
    answerList = List(default=None, scope=Scope.user_state)

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def student_view(self, context=None):
        '''
        学生页面
        '''
        if self.inStudio():
            return self.author_view(context)
        html = self.resource_string("static/html/workflow2.html")
        frag = Fragment(html)
        frag.add_css(self.resource_string("static/css/workflow2.css"))
        frag.add_javascript_url('//cdn.bootcss.com/handlebars.js/4.0.5/handlebars.min.js')
        frag.add_javascript_url('//cdn.bootcss.com/showdown/1.3.0/showdown.min.js')
        frag.add_javascript(self.resource_string("static/js/src/workflow2.js"))
        frag.initialize_js('Workflow2XBlock')
        return frag

    def author_view(self, context=None):
        '''
        Studio上的缩略页面
        '''
        content = {
            'question': self.qNo,
            'maxTry': self.maxTry
        }
        frag = Fragment(unicode(json.dumps(content)))
        return frag

    def studio_view(self, context=None):
        '''
        Studio 上的配置页面
        '''
        html = self.resource_string("static/html/workflow2_config.html")
        frag = Fragment(unicode(html).format(qNo=self.qNo, maxTry=self.maxTry))
        frag.add_javascript(self.resource_string('static/js/src/workflow2_config.js'))
        frag.initialize_js('Workflow2XBlock')
        return frag

    def inStudio(self):
        '''
        检查当前是不是studio环境
        '''
        if hasattr(self.runtime, 'get_real_user'):
            return self.runtime.get_real_user is None
        else:
            # 在测试环境
            return False

    def genCurrentStatus(self, needGradeInfo):
        if not hasattr(self.runtime, "anonymous_student_id"):
            # 测试环境
            student = Test()
            student.email = 'unkown@unkown.com'
            student.username = 'unkown'
            student.is_staff = True
            graded, gradeInfo = (False, None)
        else:
            student = self.runtime.get_real_user(self.runtime.anonymous_student_id)
            if needGradeInfo:
                graded, gradeInfo = self.fetchGradeInfo(student, self.qNo)
                self.tried, self.answerList = self.fetchAnswerInfo(student, self.qNo)
            if self.answerList is None:
                self.tried, self.answerList = self.fetchAnswerInfo(student, self.qNo)

        studentEmail = student.email
        studentUsername = student.username
        studentIsStaff = student.is_staff
        tried = self.tried
        maxTry = self.maxTry

        content = {
            'maxTry': maxTry,
            'tried': tried,
            'student': {'email': studentEmail, 'username': studentUsername, 'is_staff': studentIsStaff},
            'answer': self.answerList,
            'question': self.questionJson
        }
        if needGradeInfo:
            return dict(content, **{'graded': graded, 'gradeInfo': gradeInfo})
        else:
            return content

    def fetchGradeInfo(self, student, qNo):
        '''
        获取学生该题的批改信息
        '''
        filepath = '%(emailHash)s/%(username)s/%(qNo)d/%(qNo)d.graded.json' % {
            'emailHash': hashlib.new('md5', student.email).hexdigest()[-2:],
            'username': student.username,
            'qNo': qNo
        }
        gradeInfo = self.gitlabRepo.readContent(filepath)
        if gradeInfo is None:
            graded = False
        else:
            graded = True
        return (graded, gradeInfo)

    def fetchAnswerInfo(self, student, qNo):
        '''
        从gitlab获取学生的回答信息,并保存
        '''
        filepath = '%(emailHash)s/%(username)s/%(qNo)d/%(qNo)d.json' % {
            'emailHash': hashlib.new('md5', student.email).hexdigest()[-2:],
            'username': student.username,
            'qNo': qNo
        }
        answerInfo = self.gitlabRepo.readContent(filepath)
        if answerInfo is None:
            return (0, [])
        else:
            self.logger.info('fetch answer info from gitlab')
            return (answerInfo['tried'], answerInfo['answer'])

    @XBlock.json_handler
    def getCurrentStatus(self, data, suffix=''):
        try:
            status = self.genCurrentStatus(True)
            return {'code': 0, 'desc': 'ok', 'result': status}
        except Exception as e:
            self.logger.exception('ERROR getCurrentStatus %s' % (str(e)))
            return {'code': 1, 'dese': str(e)}

    @XBlock.json_handler
    def studentSubmit(self, data, suffix=''):
        try:
            student = self.runtime.get_real_user(self.runtime.anonymous_student_id)

            t = datetime.datetime.now() + datetime.timedelta(hours=12)
            createtime = t.strftime('%Y-%m-%d:%H:%M:%S')
            answerItem = {'time': createtime, 'answer': data['answer']}
            self.logger.debug('answerItem %s' % str(answerItem))
            self.answerList.append(answerItem)
            self.logger.debug('answerList %s' % str(self.answerList))
            self.tried += 1
            # 删除多余的历史数据
            if len(self.answerList) > Config.maxSizeOfAnswerList:
                self.answerList = self.answerList[-(Config.maxSizeOfAnswerList):]

            content = self.genCurrentStatus(False)
            # push to gitlab
            filepath = '%(emailHash)s/%(username)s/%(qNo)d/%(qNo)d.json' % {
                'emailHash': hashlib.new('md5', student.email).hexdigest()[-2:],
                'username': student.username,
                'qNo': self.qNo
            }
            oldContent = self.gitlabRepo.readContent(filepath)
            if oldContent is None:
                self.gitlabRepo.createContent(json.dumps(content, ensure_ascii=False, indent=4), filepath, 'create %s' % filepath)
            else:
                self.gitlabRepo.updateContent(json.dumps(content, ensure_ascii=False, indent=4), filepath, 'update %s' % filepath)

            self.logger.info('studentSubmit [student=%s] [tried=%d] [maxTry=%d] [answer=%s] [qNo=%d]' % (
                (student.email, student.username),
                self.tried,
                self.maxTry,
                json.dumps(answerItem),
                self.qNo
            ))
            return {'code': 0, 'desc': 'ok', 'result': self.genCurrentStatus(False)}
        except Exception as e:
            self.logger.exception('ERROR student_submit %s' % str(e))
            return {'code': 1, 'dese': str(e.args)}

    @XBlock.json_handler
    def studioSubmit(self, data, suffix=''):
        '''
        用于配置XBlock的题目，以及每个学生的回答次数
        data.q_number   题号
        data.max_try    最大尝试的次数
        '''
        try:
            self.logger.info('studioSubmit data=%s' % str(data))
            # 保存max_try
            self.maxTry = int(data['maxTry'])

            # 从github获取题号对应的题目json数据
            q_number = int(data['qNo'])
            self.qNo = q_number
            url = Config.getQuestionJsonUrl % {
                'qDir': ((q_number - 1) / 100) + 1,
                'qNo': q_number,
            }
            self.logger.info('studioSubmint url=%s' % url)
            res_data = urllib2.urlopen(url)
            res = res_data.read()
            res = json.loads(res)
            if 'content' in res:
                content = base64.b64decode(res['content'])
                self.questionJson = json.loads(content)
                self.logger.info('get question from remote [qNo=%s]' % (q_number))
                return {'code': 0, 'desc': 'ok'}
            else:
                self.logger.warning('ERROR studioSubmit: Cannot read question json [qNo=%d] [msg=%s]' % (q_number, res['message']))
                return {'code': 2, 'desc': res['message']}
        except Exception as e:
            self.logger.exception('ERROR')
            return {'code': 1, 'dese': str(e.args)}

    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("Workflow2XBlock",
             """<workflow2/>
             """),
            ("Workflow2XBlock-test",
                """
                <workflow2 maxTry="5" questionJson='{"status":"error","knowledge":["文件系统"],"degree_of_difficulty":1,"explain":"解释\n","question":"文件的逻辑结构的基本形式有**(A)**，__(B)__和__(C)__。\\n```\\n$ pip install\\n```","source":"网络","answer":"解释\n","type":"fill_in_the_blank","options":["A.", "B.", "C."],"q_number":396}'/>
             """),
            ("Multiple Workflow2XBlock",
             """<vertical_demo>
                <workflow2 maxTry="2" questionJson='{"status":"ok","knowledge":["操作系统概述"],"degree_of_difficulty":1,"explain":"B\n","question":"批处理系统的主要缺点是 。\n","source":"网络","answer":"B","type":"single_answer","options":["A.CPU的利用率不高","B.失去了交互性","C.不具备并行性","D.以上都不是"],"q_number":1002}'/>
                <workflow2 maxTry="0" questionJson='{"status":"ok","knowledge":["调查问卷"],"degree_of_difficulty":1,"explain":"解释\n","question":"为什么要学这门课？\n","source":"网络","answer":"A","type":"multi_answer","options":["A.对内容有兴趣","B.内容与自己的目标相一致，结果有用","C.由于学分要求，必须选","D.其他，请注明原因"],"q_number":1137}' answerList='[{"time":"2012-01-01 13:20","answer":"A"}]'/>
                </vertical_demo>
             """),
        ]
