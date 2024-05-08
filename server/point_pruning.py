def generate_points_per_edge_list(num_cards) -> list:
    points_per_edge = [3,5,5,5,5,3]
    num_edges = num_cards * 2
    for i in range(num_edges - 6):
        points_per_edge.insert(2,6)
    return points_per_edge

def calculate_card_count_from_points(points):
    match points:
        case x if x >= 14: return int((1/12) * (x - 2) + 1)
        case 0: return 0
        case 4: return 1
        case _: return -1

def eliminate_non_corners_and_organize_corner_points(points):
    num_cards = calculate_card_count_from_points(len(points))
    if (num_cards == 1):
        return [[points[0], points[1]],[points[2], points[3]]]
    elif (num_cards == 2):
        points_per_edge = [3,4,4,3]
        corners_points_list = []
        num_edges = len(points_per_edge)

        is_even_edge = True
        for i in range(num_edges):
            all_points_on_edges = points[sum(points_per_edge[0:i]):sum(points_per_edge[0:i+1])]
            all_points_on_edges_sorted = sorted(all_points_on_edges, key=lambda x: x[1],reverse=False)
            corners_on_edge = []
            if (is_even_edge):
                corners_on_edge = [all_points_on_edges_sorted[x] for x in range(0,points_per_edge[i],2)]
                is_even_edge = False
            elif (i == len(points_per_edge) - 1):
                corners_on_edge = [all_points_on_edges_sorted[x] for x in range(0,points_per_edge[i],2)]
            else:
                corners_on_edge = [all_points_on_edges_sorted[x] for x in range(1,points_per_edge[i],2)]
                is_even_edge = True
            corners_points_list.append(corners_on_edge)
        return corners_points_list
    else:
        points_per_edge = generate_points_per_edge_list(num_cards)
        corners_points_list = []
        is_even_edge = True
        for i in range(num_cards*2):
            all_points_on_edges = points[sum(points_per_edge[0:i]):sum(points_per_edge[0:i+1])]
            all_points_on_edges_sorted = sorted(all_points_on_edges, key=lambda x: x[1],reverse=(not is_even_edge)) # maybe take away the `not`
            corners_on_edge = []
            if (points_per_edge[i] != 3 and i != 2 and i != (num_cards * 2) - 3):
                corners_on_edge = [all_points_on_edges_sorted[0], all_points_on_edges_sorted[3]]
            else:
                corners_on_edge = [all_points_on_edges_sorted[0], all_points_on_edges_sorted[2]]
            if is_even_edge:
                is_even_edge = False
            else:
                is_even_edge = True
            corners_points_list.append(corners_on_edge)

        return corners_points_list
