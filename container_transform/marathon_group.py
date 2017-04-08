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

	#check whether the volume is already mapped
	command = "rbd showmapped | grep "+external_volume_name
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()	

	if external_volume_name in out.decode('utf-8'):
		external_volume_device=out.decode('utf-8').split(' ')[-1]
		print('**INFO: volume {0} already mapped to {1}'.format( external_volume_name, external_volume_device  ))
	else:
		#if not, map it
		command = "rbd map "+external_volume_name
		proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
		(out, err) = proc.communicate()
		#TODO error checking
		external_volume_device = out.decode('utf-8')		

	print("**DEBUG: external_volume_MAPPING {}".format(out.decode('utf-8')))

	#format the volume
	command = "mkfs.xfs -f "+external_volume_device
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()

	#unmap rbd
	command = "rbd unmap "+external_volume_name
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()
	#print("**DEBUG: output of rbd map is {}".format(out.decode('utf-8')))

	return out.decode('utf-8')

def	copy_content_to_external_volume( external_volume_name, source_path, mount_path, dest_path ):
	"""
	Copy recursively the content in localhost under "path" to the external volume.
	Assumes the path exists. Assumes the external_volume exists.
	Also creates a mount path which is where the image mounts the copied files (docker volume mount)
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

	#check whether the volume is already mapped
	command = "rbd showmapped | grep "+external_volume_name
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()	

	if external_volume_name in out.decode('utf-8'):
		output_list=out.decode('utf-8').split()
		print('**DEBUG: output list {}'.format(output_list))
		external_volume_device=output_list[-1]
		print('**INFO: volume {0} already mapped to {1}'.format( external_volume_name, external_volume_device  ))
	else:
		#if not, map it
		print('**INFO: mapping volume {0} for copy'.format( external_volume_name, out.decode('utf-8')  ))		
		command = "rbd map "+external_volume_name
		proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
		(out, err) = proc.communicate()
		#TODO error checking
		external_volume_device = out.decode('utf-8')

	#TODO error checking
	print('**INFO: volume {0} mapped to {1} for copy'.format( external_volume_name, external_volume_device ))

	#print("**DEBUG: external_volume_device {}".format(external_volume_device))
	#create mount point
	mount_point="/tmp/"+external_volume_name
	command = "mkdir -p "+mount_point
	proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()		
	print("**DEBUG: mount_point {}".format(mount_point))

	#mount the volume
	command = ("mount "+external_volume_device+" "+mount_point).replace( '\n', ' ')
	print("**DEBUG: MOUNT COMMAND {}".format(command))

	proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()

	print("**DEBUG: MOUNT command result {}".format(out.decode('utf-8')))

	#create path
	#command = "mkdir -p "+mount_point+"/"+dest_path
	#proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	#(out, err) = proc.communicate()	

	#create mount path
	print("**DEBUG: MOUNT path to be created is: {}".format(mount_point+"/"+mount_path))
	command = "mkdir -p "+mount_point+"/"+mount_path
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()	

	#recursively copy the content
	print("**DEBUG: COPY from {0} to {1}".format(source_path, mount_point+"/"+src_path))

	#copy source to src_path
	command = "cp -R "+source_path+" "+mount_point+"/"+source_path
	proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()

	#recursively copy the content
	print("**DEBUG: COPY from {0} to {1}".format(source_path, mount_point+"/"+mount_path+"/"+source_path)

	#copy source to mount_path/src_path
	command = "cp -R "+source_path+" "+mount_point+"/"+mount_path+"/"+source_path
	proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()

	#copy source to mount_path - not needed, just need to CREATE mount_path
	#command = "cp -R "+source_path+" "+mount_point+"/"+mount_path
	#proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
	#(out, err) = proc.communicate()

	#umount the volume
	command = "umount "+external_volume_device
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()	

	#unmap rbd
	command = "rbd unmap "+external_volume_name
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()
	#print("**DEBUG: output of rbd map is {}".format(out.decode('utf-8')))

	#delete temp mount point
	command = "rm -Rf "+mount_point+"/"+mount_path
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()		
	print("**DEBUG: remove mount point (should be empty) {}".format(mount_point))

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
	host_path = volume['hostPath'] 					#./app
	#first_part_of_host_path = host_path.split('/' , 1)[0]	#app
	#last_part_of_host_path = host_path.split('/' , 1)[1]		#NULL
	container_path = volume['containerPath']							#/src/app
	first_part_of_container_path = container_path[1:].split('/', 1)[0]	#src
	last_part_of_container_path = container_path[1:].split('/', 1)[1]	#app
	#create a volume 
	external_volume_name = app_name+'-'+host_path[2:].replace('/','_')
	create_external_volume( external_volume_name ) #nextcloud_apps_UUID
	#copy content from volume[hostPath] to volume
	copy_content_to_external_volume( external_volume_name, host_path, \
		first_part_of_container_path, last_part_of_container_path )
	#modify volume
	volume['external'] = { 						#mount it as external volume
		'name': external_volume_name,
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
			if portMapping.get('hostPort',{}): 	#delete ANY hostPort values, use them for VIP
				#create a VIP for every app, with a known pattern: group_dict['id']+'-'+app['id']:hostPort
				vip = "/"+group_dict['id']+'-'+app['id']+":"+str(portMapping['hostPort'])
				portMapping['labels'] = { "VIP_0": vip }
				portMapping['hostPort'] = 0
				#make the app available in MarathonLB
				if 'labels' in app:
					app['labels'].update( {"HAPROXY_GROUP": "external"} )# if there was a hostPort add to MLB
				else:
					app['labels'] = { "HAPROXY_GROUP": "external" }

		#modify all volumes in the groups apps so that "this directory" volumes become external
		for volume in app.get('container', {}).get('volumes', {}):
			if volume['hostPath'][:2] == "./":			#if the volume is "this dir" for compose
				volume = modify_volume_for_external( volume, group_dict['id']+'-'+app['id'] )	
						#modify it so that the local files are reachable via external volume

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
	input( "***DEBUG: Press ENTER to continue...")
	sys.exit(0)

