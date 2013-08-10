#!/usr/bin/env python
import os
import logging

import yaml
import arrow
import pystache
from markdown import markdown

now = arrow.utcnow()
time = now.format("HH:mm")
date = now.format("YYYY-MM-DD")
current_path = os.getcwd() + "/"

with open(current_path + "config.yaml", "r") as open_config:
    config = yaml.load(unicode(open_config.read()))

whats_where = {"input":"",
               "output": "",
               "templates": ""}

for key in whats_where:
    if config[key][0] == "/":
        whats_where[key] = config[key]
    else:
        whats_where[key] = current_path + config[key]


if not os.path.exists(whats_where["output"]):
    os.makedirs(whats_where["output"])


logger = logging.getLogger("board")
level = logging.INFO

if "log_level" in config:
    if config["log_level"] == "debug":
        level = logging.DEBUG

logger.setLevel(level)

formatter = logging.Formatter("""%(asctime)s - %(name)s - %(levelname)s
    %(message)s""")

fh = logging.FileHandler("board_build.log")
fh.setLevel(level)
fh.setFormatter(formatter)
logger.addHandler(fh)
try:
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)
except:
    pass


class configException(Exception):
    pass


class Page:
    def __init__(self, full_where):
        self.full_where = full_where
        self.which_file = self.full_where.split(whats_where["input"])[1].lstrip("/")
        with open(self.full_where, "r") as open_read_file:
            self.raw = unicode(open_read_file.read())

        raw_split = self.raw.split("+++")

        try:
            self.page_config = yaml.load(raw_split[1])
            self.raw_markdown = raw_split[2]

        except:
            logger.warn("""%s contains no config in header. Skipping build!"""
                        % self.full_where)
            raise configException("No config")

        if not "title" in self.page_config:
            logger.warn("""%s contains no title. Skipping build!"""
                        % self.full_where)
            raise configException("No title")

    def render(self, data={}):
        data.update({"time": time,
                     "date": date,
                     "site_title": config["site_title"]})
        data.update(self.page_config)

        templated_markdown = pystache.render(self.raw_markdown, data)
        data["content"] = markdown(templated_markdown)

        template = self.page_config["template"] if "template" in self.page_config else "single"
        template_path = whats_where["templates"] + "/" + template + ".html"

        with open(template_path, "r") as tmpl_data:
            raw_tmpl = unicode(tmpl_data.read())

        self.rendered_final = pystache.render(raw_tmpl, data)


    def write(self):
        write_where = ("%s/%s" % (whats_where["output"],
                                  self.which_file)).rstrip("md") + "html"

        folder = os.path.dirname(write_where)
        if not os.path.exists(folder):
            os.makedirs(folder)

        with open(write_where, "w+") as open_write_file:
            open_write_file.write(self.rendered_final)

        logger.info("Wrote %s" % write_where)


if __name__ == "__main__":
    for folder in os.walk(whats_where["input"]):
        all_files = folder[2] # files in current directory
        for single_file in all_files:
            bits = single_file.split(".")
            if bits[len(bits)-1] == "md":
                try:
                    page = Page("%s/%s" % (folder[0], single_file))
                    page.render()
                    page.write()
                except configException:
                    pass
