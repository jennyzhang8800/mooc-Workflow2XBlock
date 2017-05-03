# coding:utf8
# author:winton

import httplib
import urllib
import base64
import json
import logging


class GitRepo:
    def __init__(self, config):
        self.rootToken = config['root_token']
        self.hostname = config['hostname']
        self.port = config['port']
        self.repoId = config['repo_id']
        self.fileOperUrl = config['file_operation_url']
        self.ref = config['ref']
        self.headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}
        if config['logger'] is not None:
            self.logger = config['logger']
        else:
            self.logger = logging.getLogger('')


    def readContent(self, filepath):
        '''
        从gitlab上获取指定路径的文件内容,如果文件不存在或者发生其他问题，则返回None
        '''
        url = self.fileOperUrl % {
            'root_token': self.rootToken,
            'repo_id': self.repoId,
            'ref': self.ref,
            'filepath': filepath
        }
        conn = httplib.HTTPConnection(self.hostname, self.port, timeout=30)
        content = None
        try:
            conn.request("GET", url, None, self.headers)
            response = conn.getresponse()

            if response.status == 200:
                response_data = response.read()
                response_data = json.loads(response_data)
                content = json.loads(base64.b64decode(response_data["content"]))
            elif response.status == 404:
                pass
            else:
                msg = json.loads(response.read())['message']
                self.logger.info('readContent: wrong status returned [msg=%s] [filepath=%s]' % (msg, filepath))
        except httplib.HTTPException as e:
            self.logger.warning('Exception when get file from remote repo [%s]' % str(e))
        finally:
            conn.close()
        return content

    def createContent(self, content, filepath, commit):
        '''
        在gitlab指定路径上新建文件，返回服务器返回的信息
        '''
        url = self.fileOperUrl % {
            'root_token': self.rootToken,
            'repo_id': self.repoId,
            'ref': self.ref,
            'filepath': filepath
        }
        conn = httplib.HTTPConnection(self.hostname, self.port, timeout=60)
        conn.request("POST", url, urllib.urlencode({
            'file_path': filepath,
            'content': content,
            'branch_name': self.ref,
            'commit_message': commit
        }), self.headers)
        response = conn.getresponse()
        result = json.loads(response.read())
        if response.status == 200 or response.status == 201:
            self.logger.info('createContent: file created successfully [filepath=%s]' % (filepath))
        else:
            self.logger.warning('createContent: wrong status returned [status=%d] [msg=%s] [filepath=%s]' % (response.status, result['message'], filepath))
            raise Exception('wrong status [status=%d]' % response.status)
        return result

    def updateContent(self, content, filepath, commit):
        '''
        在gitlab上更新指定路径的文件，返回服务器返回的信息
        '''
        url = self.fileOperUrl % {
            'root_token': self.rootToken,
            'repo_id': self.repoId,
            'ref': self.ref,
            'filepath': filepath
        }
        conn = httplib.HTTPConnection(self.hostname, self.port, timeout=60)
        conn.request("PUT", url, urllib.urlencode({
            'file_path': filepath,
            'content': content,
            'branch_name': self.ref,
            'commit_message': commit
        }), self.headers)
        response = conn.getresponse()
        result = json.loads(response.read())
        if response.status == 200 or response.status == 201:
            self.logger.info('updateContent: file updated successfully [filepath=%s]' % (filepath))
        else:
            self.logger.warning('updateContent: wrong status returned [status=%d] [msg=%s] [filepath=%s]' % (response.status, result['message'], filepath))
            raise Exception('wrong status [status=%d]' % response.status)
        return result
