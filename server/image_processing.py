import numpy as np
import cv2 as cv
import uuid
import itertools as it
from PIL import Image
from point_pruning import eliminate_non_corners_and_organize_corner_points

def get_contours(image):

  # Converting to grayscale
  
  gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)

  # Applying Otsu's thresholding
  Retval, thresh = cv.threshold(gray, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)

  # Finding contours with RETR_EXTERNAL flag to get only the outer contours
  # (Stuff inside the cards will not be detected now.)
  cont, hier = cv.findContours(thresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
  # Creating a new binary image of the same size and drawing contours found with thickness -1.
  # This will colour the contours with white thus getting the outer portion of the cards.
  newthresh = np.zeros(thresh.shape, dtype=np.uint8)
  newthresh = cv.drawContours(newthresh, cont, -1, 255, -1)

  # Performing erosion->dilation to remove noise
  kernel = np.ones((3, 3), dtype=np.uint8)
  newthresh = cv.erode(newthresh, kernel, iterations=6)
  newthresh = cv.dilate(newthresh, kernel, iterations=6)

  # Again finding the final contours and drawing them on the image.
  cont, hier = cv.findContours(newthresh, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)

  return cont

def filter_contours_by_area(contours, min_area):
  filtered_contours = []
  for contour in contours:
      area = cv.contourArea(contour)
      if area >= min_area:
          filtered_contours.append(contour)
  return filtered_contours

def create_contour_mask(image, contour):
  img_copy = np.zeros(shape=image.shape)
  cv.drawContours(img_copy, [contour], -1, (255, 255, 255), 1)
  gray_copy = cv.cvtColor(np.float32(img_copy), cv.COLOR_BGR2GRAY)
  return gray_copy

def extend_line(p1, p2, distance=10000):
    diff = np.arctan2(p1[1] - p2[1], p1[0] - p2[0])
    p3_x = int(p1[0] + distance*np.cos(diff))
    p3_y = int(p1[1] + distance*np.sin(diff))
    p4_x = int(p1[0] - distance*np.cos(diff))
    p4_y = int(p1[1] - distance*np.sin(diff))
    return ((p3_x, p3_y), (p4_x, p4_y))

def find_edges(image):
  edges = cv.Canny(np.uint8(image), 70, 150, apertureSize=7)
  line_bag = []
  all_lines_found = False

  n = 30
  while not all_lines_found and n > 0:
    edges = cv.Canny(np.uint8(image), 70, 150, apertureSize=7)
    lines = cv.HoughLinesP(edges, 1, np.pi/180, threshold=70, minLineLength=50, maxLineGap=20)
    if lines is not None:
      x1, y1, x2, y2 = lines[0][0]
      (save_point_1, save_point_2) = extend_line((x1, y1), (x2, y2))
      cv.line(image, save_point_1, save_point_2, (0, 0, 0), 16) #25

      line_bag.append((save_point_1,save_point_2))
      n= n-1
    else:
      all_lines_found = True

  return line_bag

def is_within_image(point, image_shape):
    return 0 <= point[0] < image_shape[1] and 0 <= point[1] < image_shape[0]

def find_intersections(lines, image_shape):
    points = []
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            line1 = lines[i]
            line2 = lines[j]

            x1, y1 = line1[0]
            x2, y2 = line1[1]
            x3, y3 = line2[0]
            x4, y4 = line2[1]

            # Calculate the intersection point
            denominator = ((x1 - x2) * (y3 - y4)) - ((y1 - y2) * (x3 - x4))
            if denominator != 0:
                intersect_x = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
                intersect_y = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denominator

                intersect_point = intersect_x, intersect_y
                if is_within_image(intersect_point, image_shape):
                    points.append(intersect_point)

    return np.array(points, dtype=np.float32)

def sort_points_clockwise(points, epsilon=1e-8):
    sorted_points = []
    if len(points) >0:
      # Convert points to NumPy array
      points = np.array(points)

      # Calculate centroid (mean of all points)
      centroid = np.mean(points, axis=0)

      # Calculate angles of points with respect to centroid
      delta_y = points[:, 1] - centroid[1]
      delta_x = points[:, 0] - centroid[0]
      
      # Add epsilon to denominator to avoid division by zero
      angles = np.arctan2(delta_y, delta_x + epsilon)

      # Sort points based on angles
      sorted_indices = np.argsort(angles)

      # Rearrange points in clockwise order
      sorted_points = points[sorted_indices]

    return sorted_points

def normalize_card(img, corners):
    # Define the desired rectangle after transformation
    width = 200  # define your desired width
    height = 300  # define your desired height
    dst_corners = np.array([[0, 0], [width-1, 0], [width-1, height-1], [0, height-1]], dtype=np.float32)
    # Calculate the perspective transform matrix
    M = cv.getPerspectiveTransform(corners, dst_corners)

    # Apply the transformation
    warped_img = cv.warpPerspective(img, M, (width, height))

    return warped_img

def crop_array(array, percent_height, percent_width):
    height, width = array.shape[:2]
    cropped_height = int(percent_height * height)
    cropped_width = int(percent_width * width)
    cropped_array = array[:cropped_height, :cropped_width]
    return cropped_array

"""
MASTER FUNCTIONS
"""

def organize_points_into_cards(all_stack_points):
  if (len(all_stack_points) == 2):
    return [[point for tup in all_stack_points for point in tup]]
  number_points = len(all_stack_points)
  number_cards = number_points/4
  jump = 0
  index = 0
  is_even = True
  ordered_pairs = []
  while index < number_points:
      ordered_pairs.append(all_stack_points[index])
      if (index == 0 or index == number_points - 3):
        is_even = False
        index += 2
      elif (index == number_points - 1):
        index = number_points + 1
      elif (is_even):
        index += 3
        is_even = False
      else:
        index -= 1
        is_even = True
  unchunked = [point for tup in ordered_pairs for point in tup]
  chunked_list = [unchunked[i:i + 4] for i in range(0, len(unchunked), 4)]
  return chunked_list

def show_lines(lines, img):
  extended_lines_image = np.zeros(shape=img.shape)

  for line in lines:
    ((x1, y1), (x2, y2)) = line
    cv.line(extended_lines_image, (x1, y1), (x2, y2), (0, 255, 0), 6)

  cv.imshow("image", extended_lines_image)
  cv.waitKey(0)
  # lines_image = Image.fromarray(extended_lines_image)
  # lines_image.show()

def point_is_inside_contour(point, contour):
  leeway = 30
  return cv.pointPolygonTest(contour, (point[0], point[1]), True) > -leeway

def get_stacks(img):
  contours = get_contours(img)
  large_enough_contours = filter_contours_by_area(contours, 7000)
  stacks_points = []
  for contour in large_enough_contours:
    contour_mask = create_contour_mask(img, contour)
    # cv.imshow("contour", contour_mask)
    # cv.waitKey(0)
    lines = find_edges(contour_mask)
    # show_lines(lines, img)
    intersections = find_intersections(lines,img.shape)
    sorted_points = sorted(intersections, key=lambda point: point[0])
    # paired_points = [(sorted_points[i], sorted_points[i+1]) for i in range(0, len(sorted_points), 2)]
    sorted_points_within_contour = [pt for pt in sorted_points if point_is_inside_contour(pt, contour)]
    paired_points = eliminate_non_corners_and_organize_corner_points(sorted_points_within_contour)
    cards_as_points = organize_points_into_cards(paired_points)
    stacks_points.append(cards_as_points)

  return stacks_points

def point_stacks_to_card_image_stacks(player_image, point_stacks):
    image_stacks = []
    for stack in point_stacks:
        separated_cards = []
        for card_bounding_points in stack:
            if len(card_bounding_points) == 4:
                as_array = np.array(card_bounding_points, dtype=np.float32)
                sorted_bounding_points = sort_points_clockwise(as_array)
                oriented_image = normalize_card(player_image, sorted_bounding_points)
                separated_cards.append(oriented_image)
        image_stacks.append(separated_cards)
    return image_stacks

def player_image_to_index_img_stacks(player_image):
    img = np.array(player_image)
    stacks_as_points = get_stacks(img)
    stacks_as_card_images = point_stacks_to_card_image_stacks(img, stacks_as_points)
    stacks_as_index_images = [[crop_array(card_img, .25, .15) for card_img in stack] for stack in stacks_as_card_images]
    return stacks_as_index_images
