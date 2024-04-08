#!/usr/bin/env python3
import os, sys, json
from typing import TypedDict
import requests
import gzip, re


dir = os.getcwd()
working_dir = os.path.join(dir, "data")
cache_dir = "/tmp/cloc-debian-cache"


def trace(*args):
    print(*args, file=sys.stdout)


def err(*args):
    print(*args, file=sys.stderr)


# use http
# when local file is avaliable, use local file
def get_mirror_file(path) -> bytes:
    url = "http://mirrors.hust.college/debian/"
    res = requests.get(url + path)
    return res.content


# return local filename
def download_file(path) -> str:
    trace("Getting: " + path)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    file_name = path.split("/")[-1]
    file_path = os.path.join(cache_dir, file_name)
    bytes = get_mirror_file(path)
    with open(file_path, "wb") as f:
        f.write(bytes)
    return file_name


def get_list_content() -> str:
    path = "dists/stable/main/binary-amd64/Packages.gz"
    file = get_mirror_file(path)
    # extract .gz bytes
    file = gzip.decompress(file)
    return file.decode("utf-8")


def parse_list() -> dict:
    content = get_list_content()
    lists = content.split("\n\n")
    current_key = ""
    packages = {}
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

        # post process
        if "Depends" in pkg:
            pkg["Depends"] = [to_dep(x.strip()) for x in pkg["Depends"].split(",")]
        else:
            pkg["Depends"] = []
        packages[pkg["Package"]] = pkg

    return packages


class DepInfo(TypedDict):
    name: str
    arch: str
    version: str


def to_dep(dep: str) -> DepInfo:
    # if has alternative in dep, take first
    matches = re.match(r"^(.+?)(:.+?)?(\s\((.+)\))?(\s\|.+)?$", dep)
    if matches:
        return {"name": matches[1], "arch": matches[2], "version": matches[4]}
    else:
        return {"name": dep, "arch": "", "version": ""}


def get_all_dep(packages: dict, pkg: str, deps: list[str]):
    deps.append(pkg)
    if pkg in packages.keys():
        pkg = packages[pkg]
        if "Depends" in pkg:
            for i in pkg["Depends"]:
                pkgname = i["name"]
                if pkgname not in deps:
                    get_all_dep(packages, pkgname, deps)
    return deps


def main():
    trace("Getting package list...")
    lists = parse_list()

    trace("Done, total: " + str(len(lists)) + " packages.")

    trace("Building dependencies graph...")
    depmap = {}
    for key, l in lists.items():
        deps = []
        get_all_dep(lists, l["Package"], deps)
        depmap[key] = deps

    trace("Caculating dependencies count...")
    countmap = {}
    for key, deps in depmap.items():
        for d in deps:
            if d not in countmap:
                countmap[d] = 0
            countmap[d] += 1

    trace("Writing result...")
    with open("result.csv", "w") as f:
        f.write("name,refcount\n")
        for key, count in countmap.items():
            f.write(key + "," + str(count) + "\n")


main()
