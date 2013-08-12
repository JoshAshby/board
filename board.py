#!/usr/bin/python2
"""
Simple static website generator.

Board is lightly inspired by the recent release of `Hugo <>`__
There are a few minor things in Hugo that I didn't quite like, such as the lack
of support for top level pages. As a result I tried to write Board so it didn't
how the pages where arranged and organized, and instead only cares about having
pages to render.

At the heart of Board is YAML for configuration, both for the site wide
config.yaml, and the per page configuration defined by wrapping the YAML in +++
Mustache templates are used for the actual rendering of everything into a solid
web page, and as a result custom variables can be defined in the per page
config that can be subsequently used in the mustache templates. The actual
content is created with Markdown, but support for mustache variables is
supplied, meaning things like blog posts can use a "date" config value or
similar.

The only required per page config is title, and that is used for each page to
render the <tile> tag. If a page doesn't have a title in the config then it is
skipped.

The directory organization of the input directory matches that of the output,
and all .md documents will be converted into .html with the same name.
"""
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

extension = ".html"

# Grab the config and load it into a small dict for furture access
with open(current_path + "config.yaml", "r") as open_config:
    config = yaml.load(unicode(open_config.read()))

whats_where = {"input":"",
               "output": "",
               "templates": ""}

raw_extra_tmpls = {}

for key in whats_where:
    if config[key][0] == "/":
        whats_where[key] = config[key]
    else:
        whats_where[key] = current_path + config[key]

if "files" in config:
    for file_name in config["files"]:
        with open( "%s/%s%s" % (whats_where["templates"], file_name, extension)) as tmpl_raw:
            raw_extra_tmpls[file_name] = tmpl_raw.read()


# make sure the output directory exists
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


class configException(Exception):
    pass


class Page:
    """Represents a single page."""
    def __init__(self, full_where):
        """
        Go through and make sure we know where everything is, then after that
        we read in the raw file, pull out the config and check it for integrity
        and finally set the markdown and the config to internal class
        variables.

        :param full_where: The location of the raw .md file
        """
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
        """
        Runs the raw markdown through mustache, then converts it to HTML with
        markdown, and finally renders the template with the converted markdown
        to produce the final page.

        :param data: An optional dict of additional data that gets passed to
        the mustache templates while they render.
        """
        extra_tmpls = {}
        data.update({"time": time,
                     "date": date,
                     "site_title": config["site_title"]})
        data.update(self.page_config)

        for tmpl in raw_extra_tmpls:
            extra_tmpls[tmpl] = pystache.render(raw_extra_tmpls[tmpl], data)

        data.update({"files": extra_tmpls})

        templated_markdown = pystache.render(self.raw_markdown, data)
        data["content"] = markdown(templated_markdown, extensions=['extra'])

        template = self.page_config["template"] if "template" in self.page_config else "single"
        template_path = whats_where["templates"] + "/" + template + extension

        with open(template_path, "r") as tmpl_data:
            raw_tmpl = unicode(tmpl_data.read())

        self.rendered_final = pystache.render(raw_tmpl, data)


    def write(self):
        """
        Writes out the page to the output directory
        """
        write_where = ("%s/%s" % (whats_where["output"],
                                  self.which_file)).rstrip("md") + "html"

        folder = os.path.dirname(write_where)
        if not os.path.exists(folder):
            os.makedirs(folder)

        with open(write_where, "w+") as open_write_file:
            open_write_file.write(self.rendered_final)

        logger.info("Wrote %s" % write_where)


if __name__ == "__main__":
    #If we're running this stand alone, then make sure we setup a console
    #logger too.
    try:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(ch)
    except:
        pass

    #Walk through the input directory, checking to make sure the page is a .md
    #file, if it is, then we create a page object out of it, render and write
    #out the page file. If that fails, or if the file isn't a .md file, we
    #skip it. If there was a failure it'll be logged.
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
