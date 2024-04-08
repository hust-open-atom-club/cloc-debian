#!/usr/bin/env python3
import json
import os

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

dir = os.getcwd()
working_dir = os.path.join(dir, "data")


engine = create_engine(f"sqlite:///{working_dir}/data.db")
Base = declarative_base()
Session = sessionmaker(bind=engine)


class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    jsonRaw = Column(String)
    c = Column(Integer)
    cpp = Column(Integer)
    header = Column(Integer)
    golang = Column(Integer)
    all = Column(Integer)


# Create the table
Base.metadata.create_all(engine)


# Create a session
session = Session()

dataString = open(f"{working_dir}/result").read()
data = dataString.split("\n")
for line in tqdm(data):
    if line == "":
        continue
    d = json.loads(line)
    package = Package(
        name=d["Package"],
        jsonRaw=json.dumps(d["Lines"]),
        c=d.get("Lines", {}).get("C", {}).get("code", 0),
        cpp=d.get("Lines", {}).get("C++", {}).get("code", 0),
        golang=d.get("Lines", {}).get("Go", {}).get("code", 0),
        header=d.get("Lines", {}).get("C/C++ Header", {}).get("code", 0),
        all=d.get("Lines", {}).get("SUM", {}).get("code", 0),
    )
    session.add(package)


session.commit()
session.close()
