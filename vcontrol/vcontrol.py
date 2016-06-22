#!/usr/bin/env python

import argparse
import ast
import json
import os
import requests
import shutil
import subprocess
import sys
import web

def get_allowed():
    rest_url = ""
    if "ALLOW_ORIGIN" in os.environ:
        allow_origin = os.environ["ALLOW_ORIGIN"]
        host_port = allow_origin.split("//")[1]
        host = host_port.split(":")[0]
        port = str(int(host_port.split(":")[1])+1)
        rest_url = host+":"+port
    else:
        allow_origin = ""
    return allow_origin, rest_url

allow_origin, rest_url = get_allowed()

# This endpoint is just a quick way to ensure that the vcontrol API is up and running properly.
class index:
    def GET(self):
        web.header("Content-Type","text/plain")
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        return "vcontrol"

# This endpoint returns the version of vcontrol that is currently running this API.
class version:
    def GET(self):
        web.header("Content-Type","text/plain")
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        try:
            with open('VERSION', 'r') as f: v = f.read().strip()
        except:
            with open('../VERSION', 'r') as f: v = f.read().strip()
        return v

# This endpoint allows for getting the current capacity of a particular provider. Currently only supports VMWare and OpenStack.
class w_capacity:
    def GET(self, provider):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        # TODO for openstack and vmware
        return 1

'''
This endpoint allows for a new provider such as openstack or vmware to be added.
A vent instance runs on a provider. Note that a provider can only be added from localhost
of the machine running vcontrol unless the environment variable VENT_CONTROL_OPEN=true is set on the server.
'''
class w_add_provider:
    def OPTIONS(self):
        return self.POST()

    def POST(self):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        web.header('Access-Control-Allow-Headers', "Content-type")
        open_d = os.environ.get('VENT_CONTROL_OPEN')
        # TODO is this sufficient? probably not...
        if web.ctx.env["HTTP_HOST"] == 'localhost:8080' or open_d == "true":
            data = web.data()
            payload = {}
            try:
                payload = ast.literal_eval(data)
                if type(payload) != dict:
                    payload = ast.literal_eval(json.loads(data))
            except:
                return "malformed json body"

            try:
                if os.path.isfile('providers.txt'):
                    with open('providers.txt', 'r') as f:
                        for line in f:
                            if line.split(":")[0] == payload['name']:
                                return "provider already exists"
                # only get here if it didn't already return
                with open('providers.txt', 'a') as f:
                    if payload['provider'] == 'openstack' or payload['provider'] == 'vmwarevsphere':
                        f.write(payload['name']+':'+payload['provider']+':'+str(payload['cpu'])+":"+str(payload['ram'])+":"+str(payload['disk'])+":"+str(payload['args'])+'\n')
                    elif payload['provider'] == 'virtualbox':
                        f.write(payload['name']+':'+payload['provider']+'\n')
                    else:
                        f.write(payload['name']+':'+payload['provider']+':'+str(payload['args'])+'\n')
                return "successfully added provider"
            except:
                return "unable to add provider"
        else:
            return "must be done from the localhost running vcontrol daemon"

'''
This endpoint allows for removing a provider such as openstack or vmware.
A vent instance runs on a provider, this will not remove existing vent instances
on the specified provider. Note that a provider can only be removed from localhost
of the machine running vcontrol unless the environment variable VENT_CONTROL_OPEN=true is set on the server.
'''
class w_remove_provider:
    def GET(self, provider):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        open_d = os.environ.get('VENT_CONTROL_OPEN')
        if web.ctx.env["HTTP_HOST"] == 'localhost:8080' or open_d == "true":
            f = open("providers.txt","r")
            lines = f.readlines()
            f.close()
            flag = 0
            with open("providers.txt", 'w') as f:
                for line in lines:
                    if not line.startswith(provider+":"):
                        f.write(line)
                    else:
                        flag = 1
            if flag:
                return "removed " + provider
            else:
                return provider + " not found, couldn't remove"
        else:
            return "must be done from the localhost running vcontrol daemon"

# This endpoint lists all of the providers that have been added.
class w_list_providers:
    def GET(self):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        try:
            providers = {}
            if os.path.isfile('providers.txt'):
                with open('providers.txt', 'r') as f:
                    for line in f:
                        providers[line.split(":")[0]] = line.split(":")[1].strip()
            return providers
        except:
            return "unable to get providers"

# This endpoint is for creating a new instance of vent on a provider.
class w_create_instance:
    def OPTIONS(self):
        return self.POST()

    def POST(self):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        web.header('Access-Control-Allow-Headers', "Content-type")
        data = web.data()
        payload = {}
        try:
            payload = ast.literal_eval(data)
            if type(payload) != dict:
                payload = ast.literal_eval(json.loads(data))
        except:
            return "malformed json body"

        try:
            if os.path.isfile('providers.txt'):
                with open('providers.txt', 'r') as f:
                    for line in f:
                        if line.split(":")[0] == payload['provider']:
                            proc = None
                            cleanup = False
                            if line.split(":")[1] == 'openstack' or line.split(":")[1] == 'vmwarevsphere':
                                # TODO check usage stats first and make sure it's not over the limits (capacity)
                                cmd = "/usr/local/bin/docker-machine create -d "+line.split(":")[1]+" "+line.split(":")[5].strip()
                            elif line.split(":")[1].strip() == "virtualbox":
                                cmd = "/usr/local/bin/docker-machine create -d "+line.split(":")[1].strip()
                                if payload['iso'] == '/tmp/vent/vent.iso':
                                    if not os.path.isfile('/tmp/vent/vent.iso'):
                                        cleanup = True
                                        os.system("git config --global http.sslVerify false")
                                        os.system("cd /tmp && git clone https://github.com/CyberReboot/vent.git")
                                        os.system("cd /tmp/vent && make")
                                    proc = subprocess.Popen(["nohup", "python", "-m", "SimpleHTTPServer"], cwd="/tmp/vent")
                                    cmd += ' --virtualbox-boot2docker-url=http://localhost:8000/vent.iso'
                                cmd += ' --virtualbox-cpu-count "'+str(payload['cpus'])+'" --virtualbox-disk-size "'+str(payload['disk_size'])+'" --virtualbox-memory "'+str(payload['memory'])+'"'
                            else:
                                cmd = "/usr/local/bin/docker-machine create -d "+line.split(":")[1]+" "+line.split(":")[2].strip()
                            if line.split(":")[1] == "vmwarevsphere":
                                cmd += ' --vmwarevsphere-cpu-count "'+str(payload['cpus'])+'" --vmwarevsphere-disk-size "'+str(payload['disk_size'])+'" --vmwarevsphere-memory-size "'+str(payload['memory'])+'"'
                            cmd += ' '+payload['machine']
                            output = subprocess.check_output(cmd, shell=True)
                            if proc != None:
                                os.system("kill -9 "+str(proc.pid))
                            if cleanup:
                                shutil.rmtree('/tmp/vent')
                            return output
                return "provider specified was not found"
            else:
                return "no providers, please first add a provider"
        except:
            return "unable to create instance"

# This endpoint is for delete an existing instance of vent.
class w_delete_instance:
    def GET(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        data = web.input()
        cmd = "/usr/local/bin/docker-machine rm"
        if 'force' in data:
            if data['force']:
                cmd += " -f"
        cmd += " "+machine
        try:
            out = subprocess.check_output(cmd, shell=True)
        except:
            out = "unable to delete instance"
        return str(out)

# This endpoint is for starting a stopped instance.
class w_start_instance:
    def GET(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        try:
            out = subprocess.check_output("/usr/local/bin/docker-machine start "+machine, shell=True)
        except:
            out = "unable to start instance"
        return str(out)

# This endpoint is for stopping a running instance.
class w_stop_instance:
    def GET(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        try:
            out = subprocess.check_output("/usr/local/bin/docker-machine stop "+machine, shell=True)
        except:
            out = "unable to stop instance"
        return str(out)

# This endpoint is building Docker images on an instance.
class w_command_build:
    def GET(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        data = web.input()
        cmd = "/usr/local/bin/docker-machine ssh "+machine+" /bin/sh /data/build_images.sh"
        # !! TODO test with swagger
        if 'no_cache' in data:
            if not data['no_cache']:
                cmd += " --no-cache"
        try:
            out = subprocess.check_output(cmd, shell=True)
        except:
            return "failed to build"
        return "done building"

# This endpoint is for running an arbitrary command on an instance and getting the result back.
class w_command_generic:
    def OPTIONS(self, machine):
        return self.POST(machine)

    def POST(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        data = web.data()
        payload = {}
        try:
            payload = ast.literal_eval(data)
            if type(payload) != dict:
                payload = ast.literal_eval(json.loads(data))
        except:
            return "malformed json body"

        for param in data:
            p = param.split("=")
            payload[p[0]] = p[1]
        out = ""
        try:
            command = payload['command']
        except:
            out = "you must specify a command"
            return out
        try:
            cmd = "/usr/local/bin/docker-machine ssh "+machine+" \""+command+"\""
            out = subprocess.check_output(cmd, shell=True)
        except:
            out = "unable to execute generic command"
        return str(out)

# This endpoint is for rebooting a running instance.
class w_command_reboot:
    def GET(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        try:
            out = subprocess.check_output("/usr/local/bin/docker-machine restart "+machine, shell=True)
        except:
            out = "unable to reboot instance"
        return str(out)

# This endpoint is for starting a specified category of containers on a specific instance.
class w_command_start:
    def GET(self, machine, category):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        # just in case, make sure vent-management is running first
        out = ""
        try:
            out = subprocess.check_output("/usr/local/bin/docker-machine ssh "+machine+" \"python2.7 /data/template_parser.py "+category+" start\"", shell=True)
        except:
            out = "unable to start "+category+" on "+machine
        return str(out)

# This endpoint is for stopping a specified category of containers on a specific instance.
class w_command_stop:
    def GET(self, machine, category):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        try:
            out = subprocess.check_output("/usr/local/bin/docker-machine ssh "+machine+" \"python2.7 /data/template_parser.py "+category+" stop\"", shell=True)
        except:
            out = "unable to stop "+category+" on "+machine
        return str(out)

# This endpoint is for getting messages that happen on an instance.
class w_command_messages:
    def GET(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        try:
            out = subprocess.check_output("/usr/local/bin/docker-machine ssh "+machine+" \"/data/info_tools/get_messages.sh\"", shell=True)
        except:
            out = "unable to get messages from "+machine
        return str(out)

# This endpoint is for getting services that are running on an instance.
class w_command_services:
    def GET(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        try:
            out = subprocess.check_output("/usr/local/bin/docker-machine ssh "+machine+" \"/data/info_tools/get_services.sh\"", shell=True)
        except:
            out = "unable to get services from "+machine
        return str(out)

# This endpoint is for getting tasks that are running on an instance.
class w_command_tasks:
    def GET(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        try:
            out = subprocess.check_output("/usr/local/bin/docker-machine ssh "+machine+" \"/data/info_tools/get_tasks.sh\"", shell=True)
        except:
            out = "unable to get tasks from "+machine
        return str(out)

# This endpoint is for getting tools on an instance.
class w_command_tools:
    def GET(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        try:
            out = subprocess.check_output("/usr/local/bin/docker-machine ssh "+machine+" \"/data/info_tools/get_tools.sh\"", shell=True)
        except:
            out = "unable to get tools from "+machine
        return str(out)

# This endpoint is for getting types on an instance.
class w_command_types:
    def GET(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        try:
            out = subprocess.check_output("/usr/local/bin/docker-machine ssh "+machine+" \"/data/info_tools/get_types.sh\"", shell=True)
        except:
            out = "unable to get types from "+machine
        return str(out)

# This endpoint is for ssh-ing into an instance.
# !! TODO
class w_command_ssh:
    def GET(self, machine):
        # TODO
        return 1

# This endpoint is just a quick way to ensure that providers are still reachable.
class w_heartbeat_instances:
    def GET(self):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        # TODO
        return 1

# This endpoint is just a quick way to ensure that providers are still reachable.
class w_heartbeat_providers:
    def GET(self):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        # TODO
        return 1

# This endpoint lists all of the instances that have been created or registered.
class w_list_instances:
    def GET(self):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        data = web.input()
        instance_array = []
        try:
            if 'fast' in data:
                if data['fast'] == 'True':
                    if os.path.isdir('/root/.docker/machine/machines'):
                        out = subprocess.check_output("ls -1 /root/.docker/machine/machines", shell=True)
                        out = str(out)
                        out = out.split("\n")
                        for instance in out[:-1]:
                            instance_array.append(instance)
                    else:
                        out = ""
                else:
                    out = subprocess.check_output("/usr/local/bin/docker-machine ls", shell=True)
                    out = str(out)
                    out = out.split("\n")
                    for instance in out[1:-1]:
                        i = instance.split(" ")
                        instance_array.append(i[0])
            else:
                out = subprocess.check_output("/usr/local/bin/docker-machine ls", shell=True)
                out = str(out)
                out = out.split("\n")
                for instance in out[1:-1]:
                    i = instance.split(" ")
                    instance_array.append(i[0])
        except:
            pass
        return str(instance_array)

# This endpoint is for getting stats about an instance.
class w_get_stats:
    def GET(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        # TODO
        return 1

# This endpoint is for getting info about an instance.
class w_get_info:
    def GET(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        # TODO
        return 1

# This endpoint is for retrieving instance logs.
class w_get_logs:
    def GET(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        # TODO
        return 1

# This endpoint is for retrieving the template file of an instance.
class w_get_template:
    def GET(self):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        # !! TODO does this work with swagger?
        data = web.data()
        data = data.split("&")
        payload = {}
        for param in data:
            p = param.split("=")
            payload[p[0]] = p[1]
        print payload
        return 1

# This endpoint is for uploading a template file to an instance.
class w_deploy_template:
    def OPTIONS(self, machine):
        return self.POST(machine)

    def POST(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        # TODO how does this work with swagger
        x = web.input(myfile={})
        filedir = '/tmp/templates/'+machine # change this to the directory you want to store the file in.
        if not os.path.exists(filedir):
            os.makedirs(filedir)
        if 'myfile' in x: # to check if the file-object is created
            filepath=x.myfile.filename.replace('\\','/') # replaces the windows-style slashes with linux ones.
            filename=filepath.split('/')[-1] # splits the and chooses the last part (the filename with extension)
            fout = open(filedir +'/'+ filename,'w') # creates the file where the uploaded file should be stored
            fout.write(x.myfile.file.read()) # writes the uploaded file to the newly created file.
            fout.close() # closes the file, upload complete.
        # TODO scp to vent instance
        print machine
        return "successfully deployed"

# This endpoint is for registering an existing vent instance into vcontrol.
class w_register_instance:
    def OPTIONS(self):
        return self.POST()

    def POST(self):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        # generic driver
        data = web.data()
        payload = {}
        try:
            payload = ast.literal_eval(data)
            if type(payload) != dict:
                payload = ast.literal_eval(json.loads(data))
        except:
            return "malformed json body"

        try:
            # generate ssh keys
            out = subprocess.check_output('ssh-keygen -t rsa -b 4096 -C "vent-generic-'+payload['machine']+'" -f /root/.ssh/id_vent_generic_'+payload['machine']+' -q -N ""', shell=True)

            # upload public key
            out = subprocess.check_output('sshpass -p "'+payload['password']+'" scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -q /root/.ssh/id_vent_generic_'+payload['machine']+'.pub docker@'+payload['ip']+':/tmp/', shell=True)
            out = subprocess.check_output('sshpass -p "'+payload['password']+'" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -q docker@'+payload['ip']+' "cat /tmp/id_vent_generic_'+payload['machine']+'.pub >> /home/docker/.ssh/authorized_keys && rm /tmp/id_vent_generic_'+payload['machine']+'.pub"', shell=True)

            # add to docker-machine
            out = subprocess.check_output('docker-machine create -d generic --generic-ip-address "'+payload['ip']+'" --generic-ssh-key "/root/.ssh/id_vent_generic_'+payload['machine']+'" --generic-ssh-user "docker" '+payload['machine'], shell=True)
        except:
            out = "unable to register instance"
        return str(out)

# This endpoint is for deregistering an instance from vcontrol.
class w_deregister_instance:
    def GET(self, machine):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        try:
            out = subprocess.check_output("/usr/local/bin/docker-machine rm "+machine, shell=True)
        except:
            out = "unable to deregister instance"
        return str(out)

class swagger:
    def GET(self):
        # set allowed origins for api calls
        try:
            allow_origin = os.environ["ALLOW_ORIGIN"]
        except:
            allow_origin = ''
        web.header('Access-Control-Allow-Origin', allow_origin)
        try:
            with open("swagger.yaml", 'r') as f:
                filedata = f.read()
            newdata = filedata.replace("mydomain", rest_url)
            with open("swagger.yaml", 'w') as f:
                f.write(newdata)
            f = open("swagger.yaml", 'r')
        except:
            with open("../vcontrol/swagger.yaml", 'r') as f:
                filedata = f.read()
            newdata = filedata.replace("mydomain", rest_url)
            with open("../vcontrol/swagger.yaml", 'w') as f:
                f.write(newdata)
            f = open("../vcontrol/swagger.yaml", 'r')
        web.header("Content-Type","text/yaml")
        return f.read()

def get_urls():
    urls = (
        '/swagger.yaml', 'swagger',
        '/v1', 'index',
        '/v1/', 'index',
        '/v1/add_provider', 'w_add_provider',
        '/v1/remove_provider/(.+)', 'w_remove_provider',
        '/v1/capacity/(.+)', 'w_capacity',
        '/v1/create_instance', 'w_create_instance',
        '/v1/delete_instance/(.+)', 'w_delete_instance',
        '/v1/start_instance/(.+)', 'w_start_instance',
        '/v1/stop_instance/(.+)', 'w_stop_instance',
        '/v1/command_build/(.+)', 'w_command_build',
        '/v1/command_generic/(.+)', 'w_command_generic',
        '/v1/command_reboot/(.+)', 'w_command_reboot',
        '/v1/command_start/(.+)/(.+)', 'w_command_start',
        '/v1/command_stop/(.+)/(.+)', 'w_command_stop',
        '/v1/command_messages/(.+)', 'w_command_messages',
        '/v1/command_services/(.+)', 'w_command_services',
        '/v1/command_tasks/(.+)', 'w_command_tasks',
        '/v1/command_tools/(.+)', 'w_command_tools',
        '/v1/command_types/(.+)', 'w_command_types',
        '/v1/heartbeat_instances', 'w_heartbeat_instances',
        '/v1/heartbeat_providers', 'w_heartbeat_providers',
        '/v1/list_instances', 'w_list_instances',
        '/v1/list_providers', 'w_list_providers',
        '/v1/get_stats/(.+)', 'w_get_stats',
        '/v1/get_info/(.+)', 'w_get_info',
        '/v1/get_logs/(.+)', 'w_get_logs',
        '/v1/deploy_template/(.+)', 'w_deploy_template',
        '/v1/get_template', 'w_get_template',
        '/v1/register_instance', 'w_register_instance',
        '/v1/deregister_instance/(.+)', 'w_deregister_instance',
        '/v1/version', 'version'
    )
    return urls

def daemon_mode(args):
    sys.argv[1:] = ['0.0.0.0','8080']
    urls = get_urls()
    app = web.application(urls, globals())
    app.run()
    return True

# !! TODO
def capacity(args, daemon):
    return False

def add_provider(provider, args, daemon):
    # only privileged can add providers, which currently is only
    # accessible from the server running the vcontrol daemon
    open_d = os.environ.get('VENT_CONTROL_OPEN')
    if open_d != "true":
        # !! TODO get the api_v instead of hardcoding version
        daemon = 'http://localhost:8080/v1'
    if provider == "virtualbox":
        payload = {'name': args.name, 'provider': provider}
    else:
        payload = {'name': args.name, 'provider': provider, 'args': args.args}
    if provider == "openstack" or provider == "vmwarevsphere":
        payload['cpu'] = str(args.max_cpu_usage)
        payload['ram'] = str(args.max_ram_usage)
        payload['disk'] = str(args.max_disk_usage)
    r = requests.post(daemon+"/add_provider", data=json.dumps(payload))
    return r.text

def remove_provider(args, daemon):
    # only privileged can remove providers, which currently is only
    # accessible from the server running the vcontrol daemon
    open_d = os.environ.get('VENT_CONTROL_OPEN')
    if open_d != "true":
        # !! TODO get the api_v instead of hardcoding version
        daemon = 'http://localhost:8080/v1'
    r = requests.get(daemon+"/remove_provider/"+args.provider)
    return r.text

def create_instance(args, daemon):
    # first ssh into the machine running vcontrol daemon
    # from there use docker-machine to provision
    payload = {}
    payload['machine'] = args.machine
    payload['provider'] = args.provider
    payload['cpus'] = args.cpus
    payload['disk_size'] = args.disk_size
    payload['iso'] = args.iso
    payload['memory'] = args.memory
    r = requests.post(daemon+"/create_instance", data=json.dumps(payload))
    return r.text

def delete_instance(args, daemon):
    # check if controlled by docker-machine, if not fail
    # first ssh into the machine running vcontrol daemon
    # from there use docker-machine to delete
    payload = {'force':args.force}
    r = requests.get(daemon+"/delete_instance/"+args.machine, params=payload)
    return r.text

def start_instance(args, daemon):
    # check if controlled by docker-machine, if not fail
    # first ssh into the machine running vcontrol daemon
    # from there use docker-machine to start
    r = requests.get(daemon+"/start_instance/"+args.machine)
    return r.text

def stop_instance(args, daemon):
    # check if controlled by docker-machine, if not fail
    # first ssh into the machine running vcontrol daemon
    # from there use docker-machine to stop
    r = requests.get(daemon+"/stop_instance/"+args.machine)
    return r.text

def command_build(args, daemon):
    payload = {'no_cache':args.no_cache}
    r = requests.get(daemon+"/command_build/"+args.machine, params=payload)
    return r.text

def command_generic(args, daemon):
    payload = {'command':args.command}
    r = requests.post(daemon+"/command_generic/"+args.machine, data=json.dumps(payload))
    return r.text

def command_reboot(args, daemon):
    r = requests.get(daemon+"/command_reboot/"+args.machine)
    return r.text

def command_ssh(args, daemon):
    # get the certs from the machine running vcontrol daemon
    # from there ssh to the machine, whether with docker-machine or ssh

    # !! TODO check if controlled by docker-machine, if not fail (all machines should be controlled by docker-machine)
    #subprocess.call(["docker-machine ssh "+args.machine], shell=True)
    # !! TODO
    return True

def command_start(args, daemon):
    r = requests.get(daemon+"/command_start/"+args.machine+"/"+args.containers)
    return r.text

def command_stop(args, daemon):
    r = requests.get(daemon+"/command_stop/"+args.machine+"/"+args.containers)
    return r.text

def command_messages(args, daemon):
    r = requests.get(daemon+"/command_messages/"+args.machine)
    return r.text

def command_services(args, daemon):
    r = requests.get(daemon+"/command_services/"+args.machine)
    return r.text

def command_tasks(args, daemon):
    r = requests.get(daemon+"/command_tasks/"+args.machine)
    return r.text

def command_tools(args, daemon):
    r = requests.get(daemon+"/command_tools/"+args.machine)
    return r.text

def command_types(args, daemon):
    r = requests.get(daemon+"/command_types/"+args.machine)
    return r.text

def heartbeat_instances(args, daemon):
    r = requests.get(daemon+"/heartbeat_instances")
    return r.text

def heartbeat_providers(args, daemon):
    r = requests.get(daemon+"/heartbeat_providers")
    return r.text

def list_instances(args, daemon):
    payload = {'fast':args.fast}
    r = requests.get(daemon+"/list_instances", params=payload)
    return r.text

def list_providers(args, daemon):
    r = requests.get(daemon+"/list_providers")
    return r.text

def get_stats(args, daemon):
    r = requests.get(daemon+"/get_stats/"+args.machine)
    return r.text

def get_info(args, daemon):
    r = requests.get(daemon+"/get_info/"+args.machine)
    return r.text

def get_logs(args, daemon):
    r = requests.get(daemon + "/get_logs/"+args.machine)
    return r.text

def get_template(args, daemon):
    payload = {}
    payload['machine'] = args.machine
    payload['filename'] = args.filename
    r = requests.get(daemon+"/get_template", data=payload)
    return r.text

def deploy_template(args, daemon):
    files = {'myfile': open(args.path, 'rb')}
    # !! TODO how does files work with swagger?
    r = requests.post(daemon+"/deploy_template/"+args.machine, files=files)
    return True

def register_instance(args, daemon):
    # use default or supply credentials
    # use generic driver from docker-machine
    # note that they will be sent to the vcontrol daemon
    payload = {}
    payload['machine'] = args.machine
    payload['ip'] = args.ip
    payload['password'] = args.password
    r = requests.post(daemon+"/register_instance", data=json.dumps(payload))
    return r.text

def deregister_instance(args, daemon):
    r = requests.get(daemon+"/deregister_instance/"+args.machine)
    return r.text

def main(bare_metal_only, daemon, open_d, api_v):
    privileged = 0
    try:
        r = requests.get('http://localhost:8080'+api_v)
        if r.text == 'vcontrol':
            privileged = 1
    except:
        pass
    if open_d == "true":
        privileged = 1

    # generate cli and parse args
    try:
        with open('VERSION', 'r') as f: version = f.read().strip()
    except:
        with open('../VERSION', 'r') as f: version = f.read().strip()
    parser = argparse.ArgumentParser(description='vcontrol: a command line interface for managing vent instances')
    subparsers = parser.add_subparsers()

    if privileged:
        add_parser = subparsers.add_parser('add',
                                           help="add new infrastructure to run vent instances on")
        add_subparsers = add_parser.add_subparsers()
        # purposefully don't include hyper-v, fusion, etc.
        add_aws_parser = add_subparsers.add_parser('aws',
                                                   help="Public Amazon Web Services")
        add_aws_parser.add_argument('--name', '-n', default='aws',
                                    help='specify a name for the provider credentials')
        add_aws_parser.add_argument('args',
                                    help='quoted args needed for docker-machine to deploy on aws')
        add_aws_parser.set_defaults(which='add_aws_parser')
        add_azure_parser = add_subparsers.add_parser('azure',
                                                     help="Public Microsoft cloud")
        add_azure_parser.add_argument('--name', '-n', default='azure',
                                      help='specify a name for the provider credentials')
        add_azure_parser.add_argument('args',
                                      help='quoted args needed for docker-machine to deploy on azure')
        add_azure_parser.set_defaults(which='add_azure_parser')
        add_digitalocean_parser = add_subparsers.add_parser('digitalocean',
                                                            help="Public DigitalOcean cloud")
        add_digitalocean_parser.add_argument('--name', '-n', default='digitalocean',
                                             help='specify a name for the provider credentials')
        add_digitalocean_parser.add_argument('args',
                                             help='quoted args needed for docker-machine to deploy on digitalocean')
        add_digitalocean_parser.set_defaults(which='add_digitalocean_parser')
        add_exoscale_parser = add_subparsers.add_parser('exoscale',
                                                        help="Public Exoscale cloud")
        add_exoscale_parser.add_argument('--name', '-n', default='exoscale',
                                         help='specify a name for the provider credentials')
        add_exoscale_parser.add_argument('args',
                                         help='quoted args needed for docker-machine to deploy on exoscale')
        add_exoscale_parser.set_defaults(which='add_exoscale_parser')
        add_google_parser = add_subparsers.add_parser('google',
                                                      help="Public Google cloud")
        add_google_parser.add_argument('--name', '-n', default='google',
                                       help='specify a name for the provider credentials')
        add_google_parser.add_argument('args',
                                       help='quoted args needed for docker-machine to deploy on google')
        add_google_parser.set_defaults(which='add_google_parser')
        add_openstack_parser = add_subparsers.add_parser('openstack',
                                                         help="Private OpenStack cloud")
        add_openstack_parser.add_argument('--name', '-n', default='openstack',
                                          help='specify a name for the provider credentials')
        add_openstack_parser.add_argument('--max-cpu-usage', '-c', default=80, type=int,
                                          help='max percentage of cpus that can be used and still create instances (default: 80)')
        add_openstack_parser.add_argument('--max-ram-usage', '-r', default=80, type=int,
                                          help='max percentage of memory that can be used and still create instances (default: 80)')
        add_openstack_parser.add_argument('--max-disk-usage', '-d', default=80, type=int,
                                          help='max percentage of disk that can be used and still create instances (default: 80)')
        add_openstack_parser.add_argument('args',
                                          help='quoted args needed for docker-machine to deploy on openstack')
        add_openstack_parser.set_defaults(which='add_openstack_parser')
        add_rackspace_parser = add_subparsers.add_parser('rackspace',
                                                         help="Public Rackspace cloud")
        add_rackspace_parser.add_argument('--name', '-n', default='rackspace',
                                          help='specify a name for the provider credentials')
        add_rackspace_parser.add_argument('args',
                                          help='quoted args needed for docker-machine to deploy on rackspace')
        add_rackspace_parser.set_defaults(which='add_rackspace_parser')
        add_softlayer_parser = add_subparsers.add_parser('softlayer',
                                                         help="Public IBM cloud")
        add_softlayer_parser.add_argument('--name', '-n', default='softlayer',
                                          help='specify a name for the provider credentials')
        add_softlayer_parser.add_argument('args',
                                          help='quoted args needed for docker-machine to deploy on softlayer')
        add_softlayer_parser.set_defaults(which='add_softlayer_parser')
        add_virtualbox_parser = add_subparsers.add_parser('virtualbox',
                                                      help="Virtualbox for testing, can only be run locally not in a Docker container")
        add_virtualbox_parser.add_argument('--name', '-n', default='virtualbox',
                                       help='specify a name for the local provider')
        add_virtualbox_parser.set_defaults(which='add_virtualbox_parser')
        add_vmware_parser = add_subparsers.add_parser('vmware',
                                                      help="Private VMWare vSphere cloud")
        add_vmware_parser.add_argument('--name', '-n', default='vmware',
                                       help='specify a name for the provider credentials')
        add_vmware_parser.add_argument('args',
                                       help='quoted args needed for docker-machine to deploy on vmware')
        add_vmware_parser.add_argument('--max-cpu-usage', '-c', default=80, type=int,
                                       help='max percentage of cpus that can be used and still create instances (default: 80)')
        add_vmware_parser.add_argument('--max-ram-usage', '-r', default=80, type=int,
                                       help='max percentage of memory that can be used and still create instances (default: 80)')
        add_vmware_parser.add_argument('--max-disk-usage', '-d', default=80, type=int,
                                       help='max percentage of disk that can be used and still create instances (default: 80)')
        add_vmware_parser.set_defaults(which='add_vmware_parser')

    command_parser = subparsers.add_parser('command',
                                           help="command to run on vent instance")
    command_subparsers = command_parser.add_subparsers()
    cmd_build_parser = command_subparsers.add_parser('build',
                                                     help="build all of the containers on the vent instance")
    cmd_build_parser.set_defaults(which='cmd_build_parser')
    cmd_build_parser.add_argument('machine',
                                  help='machine name to build containers on')
    cmd_build_parser.add_argument('--no-cache',
                                  action='store_true',
                                  default=False,
                                  help='build containers without using cache')
    cmd_generic_parser = command_subparsers.add_parser('generic',
                                                     help="generic command to execute on the vent instance")
    cmd_generic_parser.set_defaults(which='cmd_generic_parser')
    cmd_generic_parser.add_argument('machine',
                                    help='machine name to execute command on')
    cmd_generic_parser.add_argument('command',
                                    help='command to execute')
    cmd_reboot_parser = command_subparsers.add_parser('reboot',
                                                      help="reboot a vent instance")
    cmd_reboot_parser.set_defaults(which='cmd_reboot_parser')
    cmd_reboot_parser.add_argument('machine',
                                   help='machine name to reboot')
    cmd_ssh_parser = command_subparsers.add_parser('ssh',
                                                   help="ssh to a vent instance")
    cmd_ssh_parser.set_defaults(which='cmd_ssh_parser')
    cmd_ssh_parser.add_argument('machine',
                                help='machine name to ssh into')
    cmd_messages_parser = command_subparsers.add_parser('messages',
                                                        help="get messages from a vent instance")
    cmd_messages_parser.set_defaults(which='cmd_messages_parser')
    cmd_messages_parser.add_argument('machine',
                                     help='machine name to get messages from')
    cmd_services_parser = command_subparsers.add_parser('services',
                                                        help="get services from a vent instance")
    cmd_services_parser.set_defaults(which='cmd_services_parser')
    cmd_services_parser.add_argument('machine',
                                     help='machine name to get services from')
    cmd_tasks_parser = command_subparsers.add_parser('tasks',
                                                     help="get tasks from a vent instance")
    cmd_tasks_parser.set_defaults(which='cmd_tasks_parser')
    cmd_tasks_parser.add_argument('machine',
                                  help='machine name to get tasks from')
    cmd_tools_parser = command_subparsers.add_parser('tools',
                                                     help="get tools from a vent instance")
    cmd_tools_parser.set_defaults(which='cmd_tools_parser')
    cmd_tools_parser.add_argument('machine',
                                  help='machine name to get tools from')
    cmd_types_parser = command_subparsers.add_parser('types',
                                                     help="get types from a vent instance")
    cmd_types_parser.set_defaults(which='cmd_types_parser')
    cmd_types_parser.add_argument('machine',
                                  help='machine name to get types from')
    cmd_start_parser = command_subparsers.add_parser('start',
                                                     help="start containers in a category on a vent instance")
    cmd_start_parser.set_defaults(which='cmd_start_parser')
    cmd_start_parser.add_argument('machine',
                                  help='machine name to start containers on')
    cmd_start_parser.add_argument('containers',
                                  choices=['collectors',
                                           'visualization',
                                           'active',
                                           'passive'],
                                  help='category of containers to start')
    cmd_stop_parser = command_subparsers.add_parser('stop',
                                                    help="stop containers in a category on a vent instance")
    cmd_stop_parser.set_defaults(which='cmd_stop_parser')
    cmd_stop_parser.add_argument('machine',
                                 help='machine name to stop containers on')
    cmd_stop_parser.add_argument('containers',
                                 choices=['collectors',
                                          'visualization',
                                          'active',
                                          'passive'],
                                 help='category of containers to stop')
    if not bare_metal_only:
        create_parser = subparsers.add_parser('create',
                                              help='create a new vent instance')
        create_parser.set_defaults(which='create_parser')
        create_parser.add_argument('machine',
                                   help='machine name to create')
        create_parser.add_argument('provider',
                                   help='provider to create machine on')
        create_parser.add_argument('--iso', '-i', default="/tmp/vent/vent.iso", type=str,
                                   help='URL to ISO, if left as default, it will build the ISO from source')
        create_parser.add_argument('--cpus', '-c', default=1, type=int,
                                   help='number of cpus to create the machine with (default: 1)')
        create_parser.add_argument('--disk-size', '-d', default=20000, type=int,
                                   help='disk space in MBs to create the machine with (default: 20000)')
        create_parser.add_argument('--memory', '-m', default=1024, type=int,
                                   help='memory in MBs to create the machine with (default: 1024)')
    daemon_parser = subparsers.add_parser('daemon',
                                          help='start the daemon')
    daemon_parser.set_defaults(which='daemon_parser')
    if not bare_metal_only:
        delete_parser = subparsers.add_parser('delete',
                                              help='delete a vent instance')
        delete_parser.set_defaults(which='delete_parser')
        delete_parser.add_argument('machine',
                                   help='machine name to delete')
        delete_parser.add_argument('--force', '-f',
                                   action='store_true',
                                   default=False,
                                   help='force remove instance of vent')
    deploy_parser = subparsers.add_parser('deploy',
                                          help='deploy a template to a vent instance')
    deploy_parser.set_defaults(which='deploy_parser')
    deploy_parser.add_argument('machine',
                               help='machine name to deploy template to')
    deploy_parser.add_argument('path',
                               help='file path of template to deploy')
    deregister_parser = subparsers.add_parser('deregister',
                                              help='deregister a vent instance')
    deregister_parser.set_defaults(which='deregister_parser')
    deregister_parser.add_argument('machine',
                                   help='machine name to deregister')
    get_parser = subparsers.add_parser('get',
                                       help='get files from a vent instance')
    get_subparsers = get_parser.add_subparsers()
    get_template_parser = get_subparsers.add_parser('template',
                                                    help='get a template from a vent instance')
    get_template_parser.set_defaults(which='get_template_parser')
    get_template_parser.add_argument('machine',
                                     help='machine name to get template from')
    get_template_parser.add_argument('filename',
                                     help='filename of template to get')
    heartbeat_parser = subparsers.add_parser('heartbeat',
                                             help='send a heartbeat')
    heartbeat_subparsers = heartbeat_parser.add_subparsers()
    hb_instances_parser = heartbeat_subparsers.add_parser('instances',
                                                          help='send a heartbeat to all vent instances')
    hb_instances_parser.set_defaults(which='hb_instances_parser')
    hb_providers_parser = heartbeat_subparsers.add_parser('providers',
                                                          help='send a heartbeat to all providers')
    hb_providers_parser.set_defaults(which='hb_providers_parser')
    info_parser = subparsers.add_parser('info',
                                        help='get info on a vent instance')
    info_parser.set_defaults(which='info_parser')
    info_parser.add_argument('machine',
                             help='machine name to get info from')
    list_parser = subparsers.add_parser('list',
                                        help='list all')
    list_subparsers = list_parser.add_subparsers()
    ls_instances_parser = list_subparsers.add_parser('instances',
                                                     help='list all vent instances')
    ls_instances_parser.set_defaults(which='ls_instances_parser')
    ls_instances_parser.add_argument('--fast', '-f',
                                     action='store_true',
                                     default=False,
                                     help='get the list fast, without verifying')
    ls_providers_parser = list_subparsers.add_parser('providers',
                                                     help='list all providers')
    ls_providers_parser.set_defaults(which='ls_providers_parser')
    register_parser = subparsers.add_parser('register',
                                            help='register an existing vent instance')
    register_parser.set_defaults(which='register_parser')
    register_parser.add_argument('machine',
                                 help='machine name to register')
    register_parser.add_argument('ip',
                                 help='ip address of vent machine to register')
    register_parser.add_argument('--password', '-p', default='tcuser',
                                 help='password to log into docker user on vent with (default: tcuser)')
    if privileged:
        remove_parser = subparsers.add_parser('remove',
                                              help='remove a provider')
        remove_parser.set_defaults(which='remove_parser')
        remove_parser.add_argument('provider',
                                   help='provider to remove')
    if not bare_metal_only:
        start_parser = subparsers.add_parser('start',
                                             help='start a vent instance')
        start_parser.set_defaults(which='start_parser')
        start_parser.add_argument('machine',
                                  help='machine name to start')
    stats_parser = subparsers.add_parser('stats',
                                         help='get stats of a vent instance')
    stats_parser.set_defaults(which='stats_parser')
    stats_parser.add_argument('machine',
                              help='machine name to get stats from')
    if not bare_metal_only:
        stop_parser = subparsers.add_parser('stop',
                                            help='stop a vent instance')
        stop_parser.set_defaults(which='stop_parser')
        stop_parser.add_argument('machine',
                                 help='machine name to stop')

    args = parser.parse_args()
    if args.which != "daemon_parser":
        if not daemon:
            print "Environment variable VENT_CONTROL_DAEMON not set, defaulting to http://localhost:8080"
            daemon = 'http://localhost:8080'
        try:
            r = requests.get(daemon+api_v)
            if r.text == 'vcontrol':
                #print "daemon running and reachable!"
                pass
            else:
                sys.exit()
        except:
            print "unable to reach the daemon, please start one and set VENT_CONTROL_DAEMON in your environment"
            sys.exit()

    daemon = daemon+api_v

    output = ""
    if privileged:
        if args.which == "remove_parser": output = remove_provider(args, daemon)
        if args.which == "add_aws_parser": output = add_provider("amazonec2", args, daemon)
        if args.which == "add_azure_parser": output = add_provider("azure", args, daemon)
        if args.which == "add_digitalocean_parser": output = add_provider("digitalocean", args, daemon)
        if args.which == "add_exoscale_parser": output = add_provider("exoscale", args, daemon)
        if args.which == "add_google_parser": output = add_provider("google", args, daemon)
        if args.which == "add_openstack_parser": output = add_provider("openstack", args, daemon)
        if args.which == "add_rackspace_parser": output = add_provider("rackspace", args, daemon)
        if args.which == "add_softlayer_parser": output = add_provider("softlayer", args, daemon)
        if args.which == "add_virtualbox_parser": output = add_provider("virtualbox", args, daemon)
        if args.which == "add_vmware_parser": output = add_provider("vmwarevsphere", args, daemon)

    if args.which == "cmd_build_parser": output = command_build(args, daemon)
    elif args.which == "cmd_generic_parser": output = command_generic(args, daemon)
    elif args.which == "cmd_reboot_parser": output = command_reboot(args, daemon)
    elif args.which == "cmd_ssh_parser": output = command_ssh(args, daemon)
    elif args.which == "cmd_start_parser": output = command_start(args, daemon)
    elif args.which == "cmd_stop_parser": output = command_stop(args, daemon)
    elif args.which == "cmd_messages_parser": output = command_messages(args, daemon)
    elif args.which == "cmd_services_parser": output = command_services(args, daemon)
    elif args.which == "cmd_tasks_parser": output = command_tasks(args, daemon)
    elif args.which == "cmd_tools_parser": output = command_tools(args, daemon)
    elif args.which == "cmd_types_parser": output = command_types(args, daemon)
    elif args.which == "create_parser": output = create_instance(args, daemon)
    elif args.which == "daemon_parser": output = daemon_mode(args)
    elif args.which == "delete_parser": output = delete_instance(args, daemon)
    elif args.which == "deploy_parser": output = deploy_template(args, daemon)
    elif args.which == "deregister_parser": output = deregister_instance(args, daemon)
    elif args.which == "get_template_parser": output = get_template(args, daemon)
    elif args.which == "hb_instances_parser": output = heartbeat_instances(args, daemon)
    elif args.which == "hb_providers_parser": output = heartbeat_providers(args, daemon)
    elif args.which == "info_parser": output = get_info(args, daemon)
    elif args.which == "ls_instances_parser": output = list_instances(args, daemon)
    elif args.which == "ls_providers_parser": output = list_providers(args, daemon)
    elif args.which == "register_parser": output = register_instance(args, daemon)
    elif args.which == "start_parser": output = start_instance(args, daemon)
    elif args.which == "stats_parser": output = get_stats(args, daemon)
    elif args.which == "stop_parser": output = stop_instance(args, daemon)
    else: pass # should never get here

    print output

    return

if __name__ == '__main__':
    bare_metal_only = os.environ.get('VENT_CONTROL_BARE_METAL_ONLY')
    daemon = os.environ.get('VENT_CONTROL_DAEMON')
    if not daemon:
        daemon = "http://localhost:8080"
    open_d = os.environ.get('VENT_CONTROL_OPEN')
    api_v = os.environ.get('VENT_CONTROL_API_VERSION')
    if not api_v:
        api_v = "/v1"
    main(bare_metal_only, daemon, open_d, api_v)
