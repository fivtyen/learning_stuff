import argparse
import collections
import configparser
import hashlib
import os
import re
import sys
import zlib


argparser = argparse.ArgumentParser(description="Content tracker.")
argsubparsers = argparser.add_subparsers(title="Commands", dest="command")
argsubparsers.required = True

def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)

    if  args.command == "add": 
        pass
    #     cmd_add(args)
    elif args.command == "cat-file": 
        cmd_cat_file(args)
    # elif args.command == "checkout": 
    #     cmd_checkout(args)
    # elif args.command == "commit": 
    #     cmd_commit(args)
    # elif args.command == "hash-object": 
    #     cmd_hash_object(args)
    elif args.command == "init": 
        cmd_init(args)
    # elif args.command == "log": 
    #     cmd_log(args)
    # elif args.command == "ls-tree": 
    #     cmd_ls_tree(args)
    # elif args.command == "merge": 
    #     cmd_merge(args)
    # elif args.command == "rebase": 
    #     cmd_rebase(args)
    # elif args.command == "rev-parse": 
    #     cmd_rev_parse(args)
    # elif args.command == "rm": 
    #     cmd_rm(args)
    # elif args.command == "show-ref": 
    #     cmd_show_ref(args)
    # elif args.command == "tag": 
    #     cmd_tag(args)


class GitRepository():
    worktree = None
    gitdir = None
    conf = None

    def __init__(self, path, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        if not (force or os.path.isdir(self.gitdir)):
            raise Exception("Not a git repository %s" % path)
        
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, "config")

        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif not force:
            raise Exception("Configuration file missing!")

        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0 and not force:
                raise Exception("Unsupported repositoryformatversion %s" % vers)


def repo_path(repo, *path):
    return os.path.join(repo.gitdir, *path)


def repo_file(repo, *path, mkdir=False):
    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)


def repo_dir(repo, *path, mkdir=False):
    path = repo_path(repo, *path)

    if os.path.exists(path):
        if os.path.isdir(path):
            return path
        else:
            raise Exception("Not a directory path! %s" % path)

    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None


def repo_create(path):
    repo = GitRepository(path, True)

    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception("%s is not a directory!" % path)
        if os.listdir(repo.worktree):
            raise Exception("%s is not empty!" % path)
    else:
        os.makedirs(repo.worktree)

    assert(repo_dir(repo, "branches", mkdir=True))
    assert(repo_dir(repo, "objects", mkdir=True))
    assert(repo_dir(repo, "refs", "tags", mkdir=True))
    assert(repo_dir(repo, "refs", "heads", mkdir=True))
    
    with open(repo_file(repo, "description"), "w") as f:
        f.write("Unnamed repository; edit edscription to name the repository.")

    with open(repo_file(repo, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

    with open(repo_file(repo, "config"), "w") as f:
        config = repo_default_config()
        config.write(f)

    return repo


def repo_default_config():
    ret =  configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    return ret

# init command

argsp = argsubparsers.add_parser("init", help="Initialize a new, empty repository.")
argsp.add_argument("path",
                   metavar="directory",
                   nargs="?",
                   default=".",
                   help="Where to create the repository.")


def cmd_init(args):
    repo_create(args.path)


def repo_find(path=".", required=True):
    path = os.path.realpath(path)

    if os.path.isdir(os.path.join(path, ".git")):
        return GitRepository(path)
    
    parent = os.path.realpath(os.path.join(path, ".."))

    if parent == path:
        if required:
            raise Exception("No git directory")
        else:
            return None

    return repo_find(parent, required)


class GitObject():
    """General git object class"""

    repo = None


    def __init__(self, repo, data=None):
        self.repo = repo

        if data != None:
            self.deserialize(data)

    
    def serialize(self):
        """Implemented by subclasses"""
        raise Exception("Unimplemented!")

    
    def deserialize(self, data):
        raise Exception("Unimplemented!")


def object_read(repo, sha):
    path = repo_file(repo, "objects", sha[0:2], sha[2:])

    with open(path, "rb") as f:
        raw = zlib.decompress(f.read())
        
        # Object type
        x = raw.find(b' ')
        fmt = raw[0:x]

        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode("ascii"))
        if size != len(raw)-y-1:
            raise Exception("Malformed object %s: bad length!" % sha)
        
        # if fmt ==b'commit':
        #     c = GitCommit
        # if fmt ==b'tree':
        #     c = GitTree
        # if fmt ==b'tag':
        #     c = GitTag
        if fmt == b'blob':
            c = GitBlob
        else:
            raise Exception("Unknown type %s for object %s" %(fmt.decode("ascii"), sha))

        return c(repo, raw[y+1:])


# TODO, for now a placeholder
def object_find(repo, name, fmt=None, follow=True):
    return name


def write_object(obj, actually_write=True):
    data = obj.serialize()
    result = obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data
    sha = hashlib.sha1(result).hexdigest()

    if actually_write:
        path = repo_file(obj.repo, "objects", sha[0:2], sha[2:0], mkdir=actually_write)

        with open(path, 'wb') as f:
            f.write(zlib.compress(result))

    return sha


class GitBlob(GitObject):
    fmt = b'blob'

    def serialize(self):
        return self.blobdata

    def deserialize(self, data):
        self.blobdata = data


argsp = argsubparsers.add_parser("cat-file", help="Provide content of repo objects")

argsp.add_argument("type",
                   metavar="type",
                   choices=["blob", "commit", "tag", "tree"],
                   help="Specify the type")

argsp.add_argument("object",
                   metavar="object",
                   help="The object to display")


def cmd_cat_file(args):
    repo = repo_find()
    cat_file(repo, args.object, fmt=args.type.encode())


def cat_file(repo, obj, fmt=None):
    obj = object_read(repo, object_find(repo, obj, fmt=fmt))
    sys.stdout.buffer(obj.serialize())


argsp = argsubparsers.add_parser("hash-object", 
                                 help="Compute object ID, optionally create a blob")

argsp.add_argument("-t",
                   metavar="type",
                   dest="type",
                   choices=["blob", "commit", "tree", "tag"],
                   default="blob",
                   help="Specify the type")

argsp.add_argument("-w",
                   dest="write",
                   action="store_true",
                   help="Write the object into the database")

argsp.add_argument("path",
                   help="Read object from <file>")


def cmd_hash_object(args):
    if args.write:
        repo = GitRepository(".")
    else:
        repo = None
    
    with open(args.path, "rb") as f:
        sha = object_hash(f, args.type.encode(), repo)
        print(sha)


def object_hash(f, fmt, repo=None):
    data = f.read()

    if fmt == b'commit':
        obj = GitCommit(repo, data)
    if fmt == b'tree':
        obj = GitTree(repo, data)
    if fmt == b'tag':
        obj = GitTag(repo, data)
    if fmt == b'blob':
        obj = GitBlob(repo, data)
    else:
        raise Exception("Unknown type %s" % fmt)

    return object_write(obj, repo)


def kvlm_parse(raw, start=0, dct=None):
    if not dct:
        dct = collections.OrderedDict()

    spc = raw.find(b' ', start)
    nl = raw.find(b'\n', start)
    
    if spc < 0 or nl < spc:
        assert(nl == start)
        dct[b''] == raw[start+1]
        return dct

    key = raw[start:spc]

    end = start
    while True:
        end = raw.find(b'\n', end+1)
        if raw[end+1] != ord(' '):
            break

    value = raw[spc+1:end].replace(b'\n ', b'\n')
    
    if key in dct:
        if type(dct[key]) == list:
            dct[key].append(value)
        else:
            dct[key] = [dct[key], value]
    else:
        dct[key] = value
        
    return kvlm_parse(raw, start=end+1, dct=dct)


def kvlm_serialize(kvlm):
    ret = b''
    for k in kvlm.keys():
        if k == b'':
            continue
        val = kvlm[k]
    if type(val) != list:
        val = [val]

    for v in val:
        ret += k + b' ' + (v.replace(b'\n', b'\n ')) + b'\n'

    ret += b'\n' + kvlm[b'']

    return ret


class GitCommit(GitObject):
    fmt = b'commit'

    def deserialize(self, data):
        self.kvlm = kvlm_parse(data)

    def serialize(self):
        return kvlm_serialize(self.kvlm)


argsp.argsubparsers.add_parser("log", help="Display commit log")
argsp.add_argument("commit",
                  default="HEAD",
                  nargs="?",
                  help="Commit to start at")


def cmd_log(args):
    repo = repo_find()

    print("digraph wyaglog{")
    log_graphviz(repo, object_find(repo, args.commit), set())
    print("}")

def log_graphviz(repo, sha, seen):
    if sha in seen:
        return
    seen.add(sha)

    commit = object_read(repo, sha)
    assert commit.fmt == b'commit'

    if not b'parent' in commit.kvlm.keys():
        return
    
    parents = commit.kvlm[b'parent']

    if type(parents) != list:
        parents = [parents]

    for p in parents:
        p = p.decode("ascii")
        print("c_{} -> c_{}".format(sha, p))
        log_graphviz(repo, p, seen)


class GItTreeLeaf(object):
    def __init__(self, mode, path, sha):
        self.mode = mode
        self.path = path
        self.sha = sha


def tree_parse_one(raw, start=0):
    x = raw.find(b' ', start)
    assert x-start == 5 or x-start == 6

    mode = raw[start:x]

    y = raw.find(b'\x00', x)
    path = raw[x+1:y]

    sha = hex(int.from_bytes(raw[y+1:y+21], "big"))[2:]

    return y+21, GItTreeLeaf(mode, path, sha)


def tree_parse(raw):
    pos = 0
    max = len(raw)
    ret = list()
    while pos < max:
        pos, data = tree_parse_one(raw, pos)
        ret.append(data)
    return ret


def tree_serialize(obj):
    ret = b''
    for i in obj.items:
        ret += i.mode
        ret += b''
        ret += i.path
        ret += b'\x00'
        sha = int(i.sha, 16)
        ret += sha.to_bytes(20, byteorder="big")
    return ret


class GitTree(GitObject):
    fmt = b'tree'

    def deserialize(self, data):
        self.items = tree_parse(data)

    def serialize(self):
        return tree_serialize(self)


argsp = argsubparsers.add_parser("checkout", help="Checkout a commit")
argsp.add_argument("commit", help="The commit or tree to checkout")
argsp.add_argument("path", help="The empty directory to checkout on")


def cmd_checkout(args):
    repo = repo_find()
    obj = object_read(repo, object_find(repo, args.commit))

    if obj.fmt == b"commit":
        obj = object_read(repo, obj.kvlm[b"tree"].decode("ascii"))

    if os.path.exists(args.path):
        if not os.path.isdir(args.path):
            raise Exception("Not a directory %s" % args.path)
        if os.listdir(args.path):
            raise Exception("Direcotry not empty %s " % args.path)
    else:
        os.makedirs(args.path)

    tree_checkout(repo, obj, os.path.realpath(args.path).encode())


def tree_checkout(repo, tree, path):
    for item in tree.items:
        obj = object_read(repo, item.data)
        dest = os.path.join(path, item.path)
    
    if obj.fmt == b'tree':
        os.mkdir(dest)
        tree_checkout(repo, obj, dest)
    elif obj.fmt == b'blob':
        with open(dest, "wb") as f:
            f.write(obj.blobdata)
