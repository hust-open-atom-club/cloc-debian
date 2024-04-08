#!/usr/bin/env python3
import os,sys,json
import requests
import gzip,re


dir = os.getcwd()
working_dir = os.path.join(dir, 'data')
cache_dir = "/tmp/cloc-debian-cache"

def trace(*args):
    print(*args, file=sys.stdout)

def err(*args):
    print(*args, file=sys.stderr)


# use http
# when local file is avaliable, use local file
def get_mirror_file(path) -> bytes:
    url = "http://ftp.debian.org/debian/"
    res = requests.get(url + path)
    return res.content

# return local filename
def download_file(path) -> str:
    trace("Getting: " + path)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    file_name =  path.split("/")[-1]
    file_path = os.path.join(cache_dir,file_name)
    bytes = get_mirror_file(path)
    with open(file_path, "wb") as f:
        f.write(bytes)
    return file_name

def get_list_content() -> str:
    path = "dists/stable/main/source/Sources.gz"
    file = get_mirror_file(path)
    # extract .gz bytes
    file = gzip.decompress(file)
    return file.decode("utf-8")

def parse_list() -> list:
    content = get_list_content()
    lists = content.split("\n\n")
    current_key=""
    packages = []
    for package in lists:
        lines = package.split("\n")
        if len(package.strip()) == 0:
            continue
        pkg = {"__raw": package}
        for line in lines:
            if re.match(".+:.+", line):
                key, value = line.split(":", 1)
                pkg[key] = value.strip()
                current_key = key
            elif re.match(".+:\s*", line):
                current_key = line.split(":")[0].strip()
                pkg[current_key] = []
            elif re.match(" .+", line):
                if type(pkg[current_key]) == str:
                    pkg[current_key] = pkg[current_key] + line.strip()
                else:
                    pkg[current_key].append(line.strip())
        packages.append(pkg)
    return packages


def main():
    trace("Getting package list...")
    lists = parse_list()

    trace("Done, total: " + str(len(lists)) + " packages.")

    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)
        os.chdir(cache_dir)

    if not os.path.exists(working_dir):
        os.mkdir(working_dir)


    for pkg in lists:
        try:
            dir = pkg["Directory"]
            files = [ f.split(" ")[2] for f in pkg["Files"] ]
            filenames = [ download_file(dir + "/" + file) for file in files ]
            dsc = next(( f for f in filenames if f.endswith(".dsc") ),"")

            src_dir = os.path.join(cache_dir, "__source")
            if(os.path.exists(src_dir)):
                os.system("rm -rf " + src_dir)

            ret = os.system("dpkg-source --no-check -x " + os.path.join(cache_dir, dsc)+ " " + src_dir + "> /dev/null")
            if ret == 0:
                trace("Extract OK: " + pkg["Package"])
            else:
                err("ERR: " + pkg["Package"])

            trace("Cloc: Counting...")
                
            result = os.popen("cloc --json --quiet " + src_dir, "r").read()

            with open(os.path.join(working_dir, "result"), "a") as f:
                f.write(json.dumps({
                    "Package": pkg["Package"],
                    "Path": pkg["Directory"],
                    "Lines": json.loads(result)
                }) + "\n")

            trace("Cleaning up...")
            for file in filenames:
                os.remove(os.path.join(cache_dir, file))

            trace("Done: " + pkg["Package"])
        except KeyboardInterrupt:
            err("User interrupt.")
            exit(1)
        except Exception as e:
            err(e)
            err("@")
            err(pkg)

main()
