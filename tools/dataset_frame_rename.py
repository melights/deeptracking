"""
    Rename all frames of a dataset
"""
import os

if __name__ == '__main__':
    dataset_path = "/home/mathieu/Dataset/DeepTrack/sequence/skull/1"

    files = [f for f in os.listdir(dataset_path) if os.path.splitext(f)[-1] == ".png" and 'd' not in os.path.splitext(f)[0]]
    print("Found {} files".format(len(files)))
    count = 0
    i = 0
    while count < len(files):
        filename_rgb = os.path.join(dataset_path, "{}.png".format(i))
        filename_depth = os.path.join(dataset_path, "{}d.png".format(i))
        if os.path.exists(filename_rgb) and os.path.exists(filename_depth):
            print("rename file {} to {}.png...".format(filename_rgb, count))
            os.rename(filename_rgb, os.path.join(dataset_path, "{}.png".format(count)))
            os.rename(filename_depth, os.path.join(dataset_path, "{}d.png".format(count)))
            count += 1
        i += 1