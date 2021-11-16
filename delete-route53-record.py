#!/usr/bin/env python3
import argparse
import sys

import boto

# Shoudl be static
#DEVCLUSTER_DNS_ZONE = 'tekton.codereadyqe.com.'
DEVCLUSTER_DNS_ZONE = 'ocp-gitops-qe.com.'

class NoGoZoneIsANogo(Exception):
    pass


def delete_hosted_zone(zonename):
    zone = route53.get_zone(zonename)
    if not zone:
        print("Could not find " + zonename)
        return
    records = zone.get_records()

    print("Deleting zone: " + zonename)
    for rec in records:
        if rec.type in ('NS', 'SOA'):
            continue
        zone.delete_record(rec)
        print("\tdeleted record " + rec.name)

    print("Zone " + zonename + " has been deleted.")
    zone.delete()


def delete_record(zonename, recordname):
    if not zonename.endswith("."):
        zonename += "."
    if not recordname.endswith("."):
        recordname += "."

    zone = route53.get_zone(zonename)
    if not zone:
        raise NoGoZoneIsANogo("Could not find zone for " + zonename)

    record = zone.get_a(recordname)
    if not record:
        print("Could not find record " + recordname)
        return

    print("Record " + record.name + " has been deleted.")
    zone.delete_a(record.name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f',
        action='store_true',
        default=False,
        dest='force',
        help='Force install')

    parser.add_argument('clustername')
    args = parser.parse_args()
    route53 = boto.connect_route53()

    zonename = args.clustername + '.' + DEVCLUSTER_DNS_ZONE

    if not args.force:
        print("I am about to delete the zone: " + zonename)
        reply = input(
            "Just out of sanity check, can you please confirm that's what you want [Ny]: "
        )
        if not reply or reply.lower() != 'y':
            sys.exit(0)

    delete_hosted_zone(zonename)
    delete_record(DEVCLUSTER_DNS_ZONE, "api." + zonename)
    delete_record(DEVCLUSTER_DNS_ZONE, "\\052.apps." + zonename)
