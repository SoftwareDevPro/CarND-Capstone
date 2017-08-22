#!/usr/bin/env python

import rospy
from geometry_msgs.msg import PoseStamped
from styx_msgs.msg import Lane, Waypoint
import std_msgs.msg

import waypoints_helper

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

LOOKAHEAD_WPS = 200 # Number of waypoints we will publish. You can change this number


class WaypointUpdater(object):
    def __init__(self):
        rospy.init_node('waypoint_updater')

        rospy.logwarn("WaypointUpdater starting!!!!")

        rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        rospy.Subscriber('/base_waypoints', Lane, self.base_waypoints_cb)

        # TODO: Add a subscriber for /traffic_waypoint and /obstacle_waypoint below
        self.final_waypoints_pub = rospy.Publisher('final_waypoints', Lane, queue_size=1)

        # TODO: Add other member variables you need below
        self.last_base_waypoints_lane = None

        rospy.spin()

    def pose_cb(self, msg):

        # TODO: Implement
        if self.last_base_waypoints_lane is not None:

            base_waypoints = self.last_base_waypoints_lane.waypoints

            pose = msg.pose

            # rospy.logwarn("Pose: {}".format(pose))

            # lane = self.last_base_waypoints_lane
            # lane.header = std_msgs.msg.Header()
            # lane.header.stamp = rospy.Time.now()
            # lane.waypoints = self.waypoints

            lane = Lane()
            lane.header.stamp = rospy.Time.now()

            start_index = waypoints_helper.get_closest_waypoint_index(pose, base_waypoints)
            rospy.logwarn("Start index is: {}".format(start_index))

            lane.waypoints = base_waypoints[start_index: start_index + LOOKAHEAD_WPS]

            self.final_waypoints_pub.publish(lane)

    def base_waypoints_cb(self, lane):
        # TODO: Implement
        self.last_base_waypoints_lane = lane

    def traffic_cb(self, msg):
        # TODO: Callback for /traffic_waypoint message. Implement
        rospy.logwarn("WaypointUpdater received a traffic callback")

    def obstacle_cb(self, msg):
        # TODO: Callback for /obstacle_waypoint message. We will implement it later
        rospy.logwarn("WaypointUpdater received an obstactle callback")

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

    # def get_closest_waypoint_index(self, pose, waypoints):
    #
    #     best_index = 0
    #
    #     # for index, waypoint in enumerate(waypoints):
    #     return best_index

if __name__ == '__main__':
    try:
        WaypointUpdater()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start waypoint updater node.')
