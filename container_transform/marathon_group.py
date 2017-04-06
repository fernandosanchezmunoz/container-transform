#!/usr/bin/env python3
#
# marathon_group.py: generate a Marathon Service Group out of a list of containers
#
# Author: Fernando Sanchez [ fernando at mesosphere.com ]

import json
import sys
import argparse
import subprocess
import os
import uuid

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

def create_external_volume( external_volume_name ):
	"""
	Create an RBD external volume. Assumes RBD is working in the host
	"""

	#check that the volume exists
	#command = "rbd ls | grep "+external_volume_name
	command = "docker volume ls | grep "+external_volume_name
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()	
	if external_volume_name in out.decode('utf-8'):
		print('**INFO: volume {0} already exists'.format( external_volume_name ))
		return out.decode('utf-8')
	else:
		command = "docker volume create --driver=rexray --name="+external_volume_name
		proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
		(out, err) = proc.communicate()

	#get volume dev name
	command = "rbd map "+external_volume_name
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()
	#TODO error checking
	external_volume_device = out.decode('utf-8')

	#format the volume
	command = "mkfs.xfs -f "+external_volume_device
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()

	return out.decode('utf-8')

def	copy_content_to_external_volume( external_volume_name, source_path, dest_path ):
	"""
	Copy recursively the content in localhost under "path" to the external volume.
	Assumes the path exists. Assumes the external_volume exists
	"""
	#check that the volume exists
	command = "rbd ls | grep "+external_volume_name
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()	
	if not external_volume_name in out.decode('utf-8'):
		print('**ERROR: volume {0} to copy content into not found'.format( external_volume_name ))
		return False

	#check that the local path exists
	if not os.path.isdir( source_path ):
		print('**ERROR: directory {0} to copy content from not found'.format( source_path ))
		return False		

	#get volume dev name
	command = "rbd map "+external_volume_name
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()
	#print("**DEBUG: output of rbd map is {}".format(out.decode('utf-8')))

	#TODO error checking
	external_volume_device = out.decode('utf-8')
	#print("**DEBUG: external_volume_device {}".format(external_volume_device))
	#create mount point
	mount_point="/tmp/"+external_volume_name
	command = "mkdir -p "+mount_point
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()		
	#print("**DEBUG: mount_point {}".format(mount_point))

	#mount the volume
	command = "mount "+external_volume_device+" "+mount_point
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()

	#create path
	#command = "mkdir -p "+mount_point+"/"+dest_path
	#proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	#(out, err) = proc.communicate()	

	#recursively copy the content
	command = "cp -R "+source_path+"/ "+mount_point
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()

	#umount the volume
	command = "umount "+external_volume_device
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()	

	#unmap rbd
	command = "rbd unmap "+external_volume_name
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()
	#print("**DEBUG: output of rbd map is {}".format(out.decode('utf-8')))

	return out.decode('utf-8')

def modify_volume_for_external ( volume, app_name ):
	"""
	Receives a Marathon volume definition as a dictionary that includes a local directory to load.
	Creates an external persistent volume in a docker external volume (assumed to be mounted).
	Creates the local volume structure on the external volume, and copies the contents.
	Modifies the volume to use the newly create external volume.
	Returns the new volume dictionary.
	"""

	#get firstPartOfHostPath, etc.
	host_path = volume['hostPath'][2:] 					#app
	#first_part_of_host_path = host_path.split('/' , 1)[0]	#app
	#last_part_of_host_path = host_path.split('/' , 1)[1]		#NULL
	container_path = volume['containerPath']							#/src/app
	first_part_of_container_path = container_path[1:].split('/', 1)[0]	#src
	last_part_of_container_path = container_path[1:].split('/', 1)[1]	#app
	#create a volume 
	external_volume_name = app_name+'_'+host_path.replace('/','_')
	create_external_volume( external_volume_name ) #nextcloud_apps_UUID
	#copy content from volume[hostPath] to volume
	copy_content_to_external_volume( external_volume_name, volume['hostPath'], "/"+last_part_of_container_path)
	#modify volume
	volume['external'] = { 						#mount it as external volume
		'name': host_path,
		'provider': 'dvdi',
		'options': { 
		'dvdi/driver': 'rexray'
		}
	}
	#change containerPath to the firstPiece only
	volume['containerPath'] = first_part_of_container_path	#src		
	del( volume['hostPath'] )							#external volumes do not use hostpath

	return volume

def modify_group ( group ):
	"""
	Modifies a marathon group received as a printable string to adapt the apps inside it 
	to the desired parameters.
	Adds AcceptedResourceRoles = "*"
	Deletes any hostPort values to have Marathon assign them automatically.
	Adds a label HAPROXY_GROUP=external for all hostPort values.
	If the apps mounts any volume that is local for compose (localhost), it mounts it as "external/rexray"
	Returns the group as a modified string.
	"""

	group_dict = json.loads( group )

	for app in group_dict['apps']:
		app['acceptedResourceRoles']=["*"]
		for portMapping in app.get('container',{}).get('docker',{}).get('portMappings',{}):
			if portMapping.get('hostPort',{}): 	#delete ANY hostPort values
				portMapping['hostPort'] = 0
				if 'labels' in app:
					app['labels'].update( {"HAPROXY_GROUP": "external"} )# if there was a hostPort add to MLB
				else:
					app['labels'] = { "HAPROXY_GROUP": "external" }
		#modify all volumes in the groups apps so that "this directory" volumes become external
		for volume in app.get('container', {}).get('volumes', {}):
			if volume['hostPath'][:2] == "./":				#if the volume is "this dir" for compose
				volume = modify_volume_for_external( volume, app['id'] )

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
	#detect if it's just one app - if so, get in list
	if containers[0]=="{":
		containers="["+containers+"]" 
	group = create_group( args['name'], containers ) 
	modified_group = modify_group( group )
	output_file=open( "./group.json", "w")
	print( modified_group, file=output_file )

	sys.exit(0)

