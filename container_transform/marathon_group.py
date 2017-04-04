#!/usr/bin/env python3
#
# marathon_group.py: generate a Marathon Service Group out of a list of containers
#
# Author: Fernando Sanchez [ fernando at mesosphere.com ]

import json
import sys
import argparse

def create_group ( name, containers ):
	"""
	Creates a marathon group taking a list of containers as a parameter.
	If the list has a single member if returns the member.
	"""
	output = '{ 			\
	  "id": "'+name+'",		\
	  "apps": '+containers+'\
	  }'

	return str(output)

def modify_group ( group ):
	"""
	Modifies a marathon group received as a printable string to adapt the apps inside it 
	to the desired parameters.
	Adds AcceptedResourceRoles = "*"
	Deletes any hostPort values to have Marathon assign them automatically.
	Adds a label HAPROXY_GROUP=external for all hostPort values.
	Returns the group as a modified string.
	"""

	group_dict = json.loads( group )

	for app in group_dict['apps']:
		app['acceptedResourceRoles'] += "*"
		for portMapping in app.get('container',{}).get('docker',{}).get('portMappings',{}):
			if portMapping.get('hostPort',{}): 	#delete ANY hostPort values
				portMapping['hostPort'] = 0
				if 'labels' in app:
					app['labels'] += { "HAPROXY_GROUP": "external" } #if there was a hostPort add to MLB
				else:
					app['labels'] = { "HAPROXY_GROUP": "external" }
		
	return json.dumps( group_dict )

if __name__ == "__main__":

	#parse command line arguments
	parser = argparse.ArgumentParser(description='Convert a list of containers to a Marathon Service Group.', \
		usage='marathon_group.py -i [container_list_filename] -n [group_name]'
		)
	parser.add_argument('-i', '--input', help='name of the file including the list of containers', required=True)
	parser.add_argument('-n', '--name', help='name to be given to the Marathon Service Group', required=True)	
	args = vars( parser.parse_args() )

	#remove the trailing \n from file
	containers = ""
	for line in open( args['input'], 'r' ):
		containers += line.rstrip()
	#print( create_group( args['name'], containers ) )
	group = create_group( args['name'], containers ) 
	modified_group = modify_group( group )
	print( modified_group )

	sys.exit(0)

