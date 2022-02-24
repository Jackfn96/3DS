import os
from DDDS.drive import Drive

drive = Drive(debug=True)

def test_auth():
    assert(isinstance(drive.folders, list))


def test_list():
    file_list = drive.list('flv')
    keys = file_list[0].keys()

    assert(isinstance(file_list, list))
    assert('id' in keys)
    assert('name' in keys)


def test_get_videos():
    drive.get_videos()

    assert(len(drive.ids) > 0)


def test_get_video_data():
    annotations, evaluations, readings = drive.get_video_data('2021-11-24 15-36-04 e99')
    names = [item['name'] for item in annotations+evaluations+readings]
    
    assert('Zakaria-2021-11-24 15-36-04 e99.flv.csv' in names)

# def test_download():
#     files = drive.list('csv')
#     assert(len(files) > 0)

#     file = drive.download(files[0]['id'])
#     path = drive.save_locally(file, 'text.csv')
#     size = os.path.getsize(path)

#     assert(os.path.exists(path))
#     assert(size > 0)
#     os.remove(path)