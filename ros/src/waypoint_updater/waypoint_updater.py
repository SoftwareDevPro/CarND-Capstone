#!/usr/bin/env python

import math
import rospy
from geometry_msgs.msg import PoseStamped
from styx_msgs.msg import Lane, Waypoint
import geometry_msgs.msg
import std_msgs.msg
import os
import shutil

import waypoints_helper
import numpy as np

'''
This node will publish waypoints from the car's current position to some `x` distance ahead.

As mentioned in the doc, you should ideally first implement a version which does not care
about traffic lights or obstacles.

Once you have created dbw_node, you will update this node to use the status of traffic lights too.

Please note that our simulator also provides the exact location of traffic lights and their
current status in `/vehicle/traffic_lights` message. You can use this message to build this node
as well as to verify your TL classifier.

TODO (for Yousuf and Aaron): Stopline location for each traffic light.
'''

LOOKAHEAD_WPS = 50 # Number of waypoints we will publish. You can change this number
LOOKBEHIND_WPS = 50 # coudl be reduced

miles_per_hour_to_metres_per_second = 0.44704


class WaypointUpdater(object):
    def __init__(self):
        rospy.init_node('waypoint_updater')

        rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb, queue_size=1)
        rospy.Subscriber('/current_velocity', geometry_msgs.msg.TwistStamped, self.velocity_cb, queue_size=1)
        rospy.Subscriber('/base_waypoints', Lane, self.base_waypoints_cb, queue_size=1)

        # TODO: Add a subscriber for /traffic_waypoint and /obstacle_waypoint below
        rospy.Subscriber('/traffic_waypoint', std_msgs.msg.Int32, self.traffic_cb, queue_size=1)

        self.final_waypoints_pub = rospy.Publisher('final_waypoints', Lane, queue_size=1)

        # TODO: Add other member variables you need below
        self.last_base_waypoints_lane = None
        self.upcoming_traffic_light_waypoint_id = None
        self.upcoming_traffic_light_message_time = None
        self.current_linear_velocity = None
        self.pose = None

        # Defines braking path for a red light
        self.braking_path_waypoints = None

        # For debugging purposes only
        self.last_saved_final_points_start_index = -10

        self.waypoints_dir = "/tmp/waypoints/"
        shutil.rmtree(self.waypoints_dir, ignore_errors=True)

        if not os.path.exists(self.waypoints_dir):
            os.makedirs(self.waypoints_dir)

        self.previous_debug_time = rospy.get_rostime()

        self.loop()

    def loop(self):

        # Based on suggestions from
        # https://github.com/amakurin/CarND-Capstone/commit/9809bc60d51c06174f8c8bfe6c40c88ec1c39d50
        rate = rospy.Rate(10)
        while not rospy.is_shutdown():

            arguments = [self.last_base_waypoints_lane, self.current_linear_velocity, self.pose]
            are_arguments_available = all([x is not None for x in arguments])

            # TODO: Implement
            if are_arguments_available:

                base_waypoints = self.last_base_waypoints_lane.waypoints

                waypoints_matrix = waypoints_helper.get_waypoints_matrix(base_waypoints)

                lane = Lane()
                lane.header.stamp = rospy.Time.now()

                car_waypoint_index = waypoints_helper.get_closest_waypoint_index(self.pose.position, waypoints_matrix)

                final_waypoints = waypoints_helper.get_sublist_covered(
                    base_waypoints, car_waypoint_index, LOOKAHEAD_WPS, LOOKBEHIND_WPS)

                lane.waypoints = waypoints_helper.get_smoothed_out_waypoints(final_waypoints)
                lane.waypoints = lane.waypoints[LOOKBEHIND_WPS:]

                for index in range(len(lane.waypoints)):
                    lane.waypoints[index].twist.twist.linear.x = 15.0 * miles_per_hour_to_metres_per_second

                is_red_light_ahead = self.upcoming_traffic_light_waypoint_id is not None and \
                                     self.upcoming_traffic_light_waypoint_id > car_waypoint_index

                if is_red_light_ahead and not self.is_traffic_light_message_stale():

                    # We don't have a braking path for this light yet
                    if self.braking_path_waypoints is None:

                        relative_traffic_light_waypoint_id = \
                            self.upcoming_traffic_light_waypoint_id - car_waypoint_index

                        distance_to_traffic_light = waypoints_helper.get_road_distance(
                            lane.waypoints[:relative_traffic_light_waypoint_id])

                        # If we are close enough to traffic light that need to start braking
                        if distance_to_traffic_light < 5.0 * self.current_linear_velocity:

                            # Get braking path
                            self.braking_path_waypoints = waypoints_helper.get_braking_path_waypoints(
                                lane.waypoints, self.current_linear_velocity, relative_traffic_light_waypoint_id)

                            lane.waypoints = self.braking_path_waypoints

                    # We already have a braking path
                    else:

                        # rospy.logwarn("Continued braking path ")
                        # for index, waypoint in enumerate(self.braking_path_waypoints):
                        #     rospy.logwarn("{} -> {}".format(index, waypoint.twist.twist.linear.x))

                        braking_path_waypoints_matrix = waypoints_helper.get_waypoints_matrix(
                            self.braking_path_waypoints)

                        car_waypoint_index_in_braking_path = waypoints_helper.get_closest_waypoint_index(
                            self.pose.position, braking_path_waypoints_matrix)

                        rospy.logwarn("Copying from {} with velocity {}".format(
                            car_waypoint_index_in_braking_path,
                            self.braking_path_waypoints[car_waypoint_index_in_braking_path].twist.twist.linear.x
                        ))

                        for index, braking_path_waypoint in enumerate(
                                self.braking_path_waypoints[car_waypoint_index_in_braking_path:]):

                            lane.waypoints[index].twist.twist.linear.x = braking_path_waypoint.twist.twist.linear.x

                        for waypoint in lane.waypoints[len(self.braking_path_waypoints):]:

                            waypoint.twist.twist.linear.x = -1

                else:

                    # Set braking path to None, as we aren't braking now
                    self.braking_path_waypoints = None

                self.final_waypoints_pub.publish(lane)

                # # Save submitted path roughly every x points
                # if self.last_saved_final_points_start_index + 50 < car_waypoint_index:
                #
                #    path = os.path.join(self.waypoints_dir, "final_waypoints_{}.txt".format(car_waypoint_index)
                #     waypoints_helper.save_waypoints(lane.waypoints, path)
                #     self.last_saved_final_points_start_index = car_waypoint_index
                #
                current_time = rospy.get_rostime()
                ros_duration_since_debug = current_time - self.previous_debug_time

                duration_since_debug_in_seconds = \
                    ros_duration_since_debug.secs + (1e-9 * ros_duration_since_debug.nsecs)

                if duration_since_debug_in_seconds > 0.5:
                    rospy.logwarn("Current waypoint: {}".format(car_waypoint_index))
                    self.previous_debug_time = current_time

            rate.sleep()

    def pose_cb(self, msg):

        self.pose = msg.pose

    def base_waypoints_cb(self, lane):
        # TODO: Implement
        self.last_base_waypoints_lane = lane

        # if not os.path.exists(path):
        #     waypoints_helper.save_waypoints(lane.waypoints, path)

    def traffic_cb(self, msg):

        # TODO: Callback for /traffic_waypoint message. Implement
        self.upcoming_traffic_light_waypoint_id = msg.data
        self.upcoming_traffic_light_message_time = rospy.get_rostime()

    def is_traffic_light_message_stale(self):

        ros_duration = rospy.get_rostime() - self.upcoming_traffic_light_message_time
        duration_in_seconds = ros_duration.secs + (1e-9 * ros_duration.nsecs)
        return duration_in_seconds > 0.25

    def obstacle_cb(self, msg):
        # TODO: Callback for /obstacle_waypoint message. We will implement it later
        pass

    def get_waypoint_velocity(self, waypoint):
        return waypoint.twist.twist.linear.x

    def set_waypoint_velocity(self, waypoints, waypoint, velocity):
        waypoints[waypoint].twist.twist.linear.x = velocity

    def distance(self, waypoints, wp1, wp2):
        dist = 0
        dl = lambda a, b: math.sqrt((a.x-b.x)**2 + (a.y-b.y)**2 + (a.z-b.z)**2)
        for i in range(wp1, wp2+1):
            dist += dl(waypoints[wp1].pose.pose.position, waypoints[i].pose.pose.position)
            wp1 = i
        return dist

    def velocity_cb(self, message):
        self.current_linear_velocity = message.twist.linear.x

if __name__ == '__main__':
    try:
        WaypointUpdater()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start waypoint updater node.')
