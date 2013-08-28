import time
from ssh_helper import run_cmd, scp_to, scp_from
from chef import Node, Client


class OSNode:
    def __init__(self, ip, user, password,
                 config_manager=None, provisioner=None):
        self.ip = ip
        self.user = user
        self.password = password
        self.provisioner = provisioner
        self.config_manager = config_manager
        self.resources = []

    def run_cmd(self, remote_cmd, user=None, password=None, quiet=False):
        user = user or self.user
        password = password or self.password
        run_cmd(self.ip, remote_cmd=remote_cmd, user=user, password=password,
                quiet=quiet)

    def scp_to(self, local_path, user=None, password=None, remote_path=""):
        user = user or self.user
        password = password or self.password
        scp_to(self.ip, local_path, user=user, password=password,
               remote_path=remote_path)

    def scp_from(self, remote_path, user=None, password=None, local_path=""):
        user = user or self.user
        password = password or self.password
        scp_from(self.ip, remote_path, user=user, password=password,
                 local_path=local_path)

    def __str__(self):
        return "Node: %s" % self.ip

    def tearDown(self):
        raise NotImplementedError


class OSDeployment:
    def __init__(self, name):
        self.name
        self.nodes = []
        self._cleanups = []

    def tearDown(self):
        for node in self.nodes:
            node.tearDown()
        self.clean_up()

    def cleanUp(self):
        for cleanup in self._cleanups:
            function, args, kwargs = cleanup
            function(*args, **kwargs)

    def addCleanup(self, function, *args, **kwargs):
        self._cleanups.append((function, args, kwargs))


class ChefRazorOSDeployment(OSDeployment):
    def __init__(self, name, chef, razor, remote_chef=None):
        super(ChefRazorOSDeployment, self).__init__(name)
        self.chef = chef
        self.remote_chef = remote_chef
        self.razor = razor

    def createNode(self):
        node = next(self.chef)
        config_manager = ChefConfigManager(node.name, self.chef)
        am_id = node.attributes['razor_metadata']['razor_active_model_uuid']
        provisioner = RazorProvisioner(self.razor, am_id)
        ip = node['ipaddress']
        user = "root"
        password = provisioner.getPassword()
        osnode = OSNode(ip, user, password, config_manager, provisioner)
        osnode.addCleanup(osnode.run_cmd("reboot 0"))
        osnode.addCleanup(time.sleep(15))
        self.nodes.append(osnode)
        return osnode


class Provisioner():
    def tearDown(self):
        raise NotImplementedError


class ConfigManager():
    def tearDown(self):
        raise NotImplementedError


class ChefConfigManager(ConfigManager):
    def __init__(self, name, chef, remote_chef=None):
        self.name = name
        self.chef = chef
        self.remote_chef = remote_chef

    def __str__(self):
        return "Chef Node: %s - %s" % (self.name, self.ip)

    def tearDown(self):
        node = Node(self.name, self.api)
        Client(self.name).delete()
        node.delete()


class RazorProvisioner(Provisioner):
    def __init__(self, razor, id):
        self.razor = razor
        self._id = id

    def tearDown(self):
        self.razor.remove_active_model(self._id)

    def getPassword(self):
        return self.razor.get_active_model_pass(self._id)['password']