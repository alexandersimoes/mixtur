import os, sys
print sys.path
sys.exit()
import os, sys, mixtur
from PIL import Image, ImageOps
from shutil import copyfile

mixes = mixtur.query_db("select * from mix;")
for m in mixes:
    print m['id'], m['slug']
    if not m['slug'] or not m['cover']: continue
    mix_dir = os.path.join(mixtur.app.config['UPLOAD_FOLDER'], m['user'], str(m['slug']))
    
    lg_file_path = os.path.join(mix_dir, m['cover'])
    
    if os.path.isfile(lg_file_path):
        filename_no_ext, file_extension = os.path.splitext(m['cover'])
        copyfile(lg_file_path, os.path.join(mix_dir, filename_no_ext+"_copy"+file_extension))
        thumb_file_path = os.path.join(mix_dir, filename_no_ext+"_thumb"+file_extension)
    
        MAX_SIZE = 1600
        QUALITY = 80
        image = Image.open(lg_file_path)
        original_size = max(image.size[0], image.size[1])

        if original_size >= MAX_SIZE:
            if (image.size[0] > image.size[1]):
                resized_width = MAX_SIZE
                resized_height = int(round((MAX_SIZE/float(image.size[0]))*image.size[1])) 
            else:
                resized_height = MAX_SIZE
                resized_width = int(round((MAX_SIZE/float(image.size[1]))*image.size[0]))

            full_image = image.resize((resized_width, resized_height), Image.ANTIALIAS)
            full_image.save(lg_file_path, image.format, quality=QUALITY)
    
        thumb_image = ImageOps.fit(image, (500,500), Image.ANTIALIAS)
        thumb_image.save(thumb_file_path, image.format, quality=90)
    else:
        print
        print 'No File for mix', m
        print
    
    # sys.exit()