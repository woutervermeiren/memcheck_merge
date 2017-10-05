#!/usr/bin/env python

"""
 memcheck_merge

 Merges individual memcheck xml files into one file

 Author: Wouter Vermeiren
 License: MIT License - http://www.opensource.org/licenses/mit-license.php
"""
import argparse
import logging
import os
import sys
import glob
import xml.dom.minidom as minidom
from xml.parsers.expat import ExpatError

OUTPUT_FILE_TEMPLATE = """\
<?xml version="1.0"?>

<valgrindoutput>

<protocolversion>4</protocolversion>
<protocoltool>memcheck</protocoltool>

<preamble>
  <line>Memcheck, a memory error detector</line>
  <line>Copyright (C) 2002-2015, and GNU GPL'd, by Julian Seward et al.</line>
  <line>Using Valgrind-3.12.0 and LibVEX; rerun with -h for copyright info</line>
  <line>Command: vce --gtest_filter=-*.CheckDebugRoutines</line>
</preamble>

<pid>12345</pid>
<ppid>67890</ppid>
<tool>memcheck</tool>

<args>
  <vargv>
    <exe>/ap/local/potatools/valgrind/3.12.0/bin/valgrind</exe>
    <arg>--suppressions=.config/valgrind/valgrind.suppress</arg>
    <arg>--leak-check=full</arg>
    <arg>--child-silent-after-fork=yes</arg>
    <arg>--xml=yes</arg>
    <arg>--xml-file=memcheck.xml</arg>
  </vargv>
  <argv>
    <exe>vce</exe>
    <arg>--gtest_filter=-*.CheckDebugRoutines</arg>
  </argv>
</args>

<status>
  <state>RUNNING</state>
  <time>00:00:00:00.000 </time>
</status>


<status>
  <state>FINISHED</state>
  <time>00:00:00:00.000 </time>
</status>

<error />

<errorcounts>
</errorcounts>

<suppcounts>
  <pair>
    <count>166</count>
    <name>possibly_lost_in_string_alloc</name>
  </pair>
</suppcounts>

</valgrindoutput>
"""

def print_results(len_error_xml_nodes=0, len_unparsable_files=0):
	"""
	Print the results in a nice way
	"""
	error_msg = '!!!'

	if len_error_xml_nodes > 0:
		error_msg += ' Found'
		if len_error_xml_nodes==1:
			error_msg += ' 1 error'
		else:
			error_msg += ' {} errors'.format(len_error_xml_nodes)
	if len_unparsable_files > 0:
		if not error_msg:
			error_msg += ' Found'
		else:
			error_msg += ','
		if len_unparsable_files==1:
			error_msg += ' 1 unparsable file'
		else:
			error_msg += ' {} unparsable files.'.format(len_unparsable_files)
	if error_msg != '!!!':
		logging.error(error_msg)
	else:
		logging.info('No memcheck errors or parsing issues encountered.')


def clean_and_check_directory(dir_name):
	"""
	Make sure the directory name does NOT end with a slash and check if it exists
	"""
	if dir_name.endswith('/'):
		dir_name = dir_name[:-1]
	return (dir_name, os.path.exists(dir_name) and os.path.isdir(dir_name))


def main(source_dir, output_file):
	"""
	Scan memcheck result files and combine them into one file
	"""
	logging.info('Scanning %s', source_dir)

	search_pattern = '{}/*.xml'.format(source_dir)
	logging.debug('1) Scanning for xml files using: %s', search_pattern)

	error_xml_nodes = []
	unparsable_files = []
	doc = None
	for xml_file in glob.glob(search_pattern):
		if os.stat(xml_file).st_size != 0:
			logging.debug('Processing %s', xml_file)
			try:
				doc = minidom.parse(xml_file)
				try:
					errors = doc.getElementsByTagName('error')
					if errors:
						logging.error(' ERROR | Found %d errors in %s', len(errors), xml_file)
						error_xml_nodes.extend(errors)
				except AttributeError:
					logging.debug('  OK   | %s', xml_file)
			except ExpatError:
				logging.error(' ERROR | Could not parse %s', xml_file)
				unparsable_files.append(xml_file)

	logging.debug('2) Put all errors into new output file %s', output_file)
	print_results(len(error_xml_nodes), len(unparsable_files))

	logging.debug('3) Use xml template to generate one file')
	output_file_template = minidom.parseString(OUTPUT_FILE_TEMPLATE)

	template_error_node = output_file_template.getElementsByTagName('error')[0]
	parent_node = template_error_node.parentNode
	if error_xml_nodes:
		for error_xml_node in error_xml_nodes:
			logging.debug('Insert error node: %s', error_xml_node.toprettyxml(indent='', newl=''))
			parent_node.insertBefore(error_xml_node, template_error_node)
	logging.debug('Removing obsolete node: %s', template_error_node.toprettyxml(indent='', newl=''))
	parent_node.removeChild(template_error_node)


	logging.debug('4) Write output file')
	logging.info('Writing results into %s', output_file)
	with open(output_file, 'wb') as output_file_handle:
		output_file_template.writexml(output_file_handle)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Merge multiple memcheck files into one file")
	parser.add_argument('-s', '--source-directory', dest='source_dir', default=os.getcwd(), \
			help='Start scanning for xml files from this directory')
	parser.add_argument('-o', '--output-directory', dest='output_dir', \
			help='Directory where the xml file will be saved. By default this is the same as the source directory.')
	parser.add_argument('-f', '--output-file', dest='output_file', default='output.xml', required=True, \
			help='Filename for the output file, saved inside the output directory.')
	parser.add_argument('-v', '--verbose', dest='be_verbose', action='store_true')

	args = parser.parse_args()
	valid_args = True

	# setup logging
	logging.basicConfig(level=logging.INFO, format='')
	if(args.be_verbose):
		logging.getLogger().setLevel(logging.DEBUG)

	# handle source dir
	(source_dir, dir_exists) = clean_and_check_directory(args.source_dir)
	if not dir_exists:
		logging.error('!!! %s does not exist.', source_dir)
		valid_args = False

	# handle output dir
	if args.output_dir is None:
		args.output_dir = source_dir
	(output_dir, dir_exists) = clean_and_check_directory(args.output_dir)
	if not dir_exists:
		logging.error('!!! %s does not exist.', output_dir)
		valid_args = False

	# handle output file
	output_file = args.output_dir + '/' + args.output_file

	if valid_args:
		main(source_dir, output_file)
	else:
		sys.exit(1)
