#--------------------------
# IniPort: For parsing and writing Ini file content.
# 05.03.2022
#--------------------------
# Robin Hohnsbeen (Ryou)

import os
from pathlib import Path

def Read(filepath):
	file_content = []

	file = None
	if os.path.exists(filepath):
		try:
			# opening the file in read mode
			file = open(filepath, "r")
			lines = file.readlines()
			current_section_index = -1
			
			for line in lines:
				if line == "\n":
					continue
				
				line = line.strip()
				
				if line.startswith("["):
					section_content = {}
					section_content["SectionName"] = line
					current_section_index += 1
					file_content.append(section_content)
				
				elif current_section_index > -1:
					section_content = file_content[current_section_index]
					name_and_values = line.split("=", 1)
					section_content[name_and_values[0].strip()] = name_and_values[1].strip()
					file_content[current_section_index] = section_content

			path = Path(filepath)
			print("Finished reading " + path.name)
		
		except:
			print("There is no file at path " + filepath)

		finally:
			if file:
				file.close()
			
	return file_content

def Write(filepath, file_content):
	messagetype = "INFO"
	message = "Success"
	
	file = None
	try:
		file = open(filepath, "w")
		
		for section_content in file_content:
			for entry_key in section_content:
				entry = section_content[entry_key]
				if entry_key == "SectionName":
					file.write(entry + "\n")
				else:
					file.write(entry_key + "=" + entry + "\n")
			
			file.write("\n")

		path = Path(filepath)
		print("Finished writing at" + path)

	except:
		print("Could not open file at " + filepath)
		messagetype = "ERROR"
		message = "Could not open file at " + filepath

	finally:
		if file:
			file.close()

	return messagetype, message