import os
import configparser
import logging
import datetime
import pathlib
from . import utils

import azure.functions as func

def email_wrapper(p, to_user, to_email, email_body):

	api_key = p['EMAIL']['O365ID']
	secret = p['EMAIL']['O365SECRET']
	from_email = p['EMAIL']['FROMEMAIL']

	if to_user:
		subject = 'AGOL Credit checker: {}'.format(to_user) 
	else:
		subject = "Weekly AGOL Feature Service Report"

	utils.send_o365(api_key, secret, from_email, to_email, email_body, subject)

	return

def find_email(user_list, user_name):

	for u in user_list:
		if user_name == u['username']:
			return u['email']
	return None

def parse_admin(org_info):

	expire = utils.nice_date(org_info['expDate'])
	credits_available = org_info['availableCredits']
	return expire, credits_available


def main(mytimer: func.TimerRequest) -> None:

	utc_timestamp = datetime.datetime.utcnow().replace(
		tzinfo=datetime.timezone.utc).isoformat()
    
	if mytimer.past_due:
		logging.info('The timer is past due!')
	logging.info('Started AGOL Credit checker at %s', utc_timestamp)

	parser = configparser.ConfigParser()
	parser.read(os.path.join(pathlib.Path(__file__).parent, "config.ini"))
	admin_user = parser['AGOL']['USER']
	url = parser['AGOL']['URL']

	debug = parser['SETUP'].getboolean('DEBUG')
	to_email_dbg = parser['SETUP']['TOEMAIL']

	CM = utils.AGOL_Manager(admin_user, parser['AGOL']['PASS'], url)

	all_fs_size = 0
	all_credits_month = 0
	total_items = 0
	admin_user_list_items = []
	for key, value in CM.itms.items(): 
		user_name = key
		user_items = []
		totalSize = 0
		pop = ['owner', 'type']
		
		for itm in CM.itms[user_name]:
			for p in pop:
				itm.pop(p)
			itm['modified'] = utils.nice_date(itm['modified'])
			itm['created'] = utils.nice_date(itm['created'])
			totalSize += itm['size'] / 1024 / 1024 # mb
			itm['size'] = "{} mb".format(round(itm['size'] / 1024 / 1024, 2))
			itm['url'] = "<a href='{}'>FS URL</a>".format(itm['url'])
			itm['itemID'] = "<a href='{}/home/item.html?id={}'>AGOL Item</a>".format(CM.url, itm['itemID'])
			user_items.append(itm)
			total_items += 1

		# https://doc.arcgis.com/en/arcgis-online/administer/credits.htm
		creditsUsedPerMonth = (totalSize / 10) * 2.4
		creditsUsedPerWeek = creditsUsedPerMonth / 4
		# credits cost 16cents (1000 / $160)
		costPerWeeek = creditsUsedPerWeek * 0.16

		admin_user_list_items.append({"user": user_name,
							"Num of items" : len(CM.itms[user_name]),
							"Credits Burned": round(costPerWeeek, 2),
							"Total FS Size": "{} mb".format(round(totalSize, 2))
							})

		all_fs_size += totalSize
		all_credits_month += creditsUsedPerMonth
		
		html = utils.html_table(user_items)
		masterHTML = "<html>{}".format(utils.style)
		masterHTML += "<body><h2>FS Credit usage for: {}</h2>".format(user_name)
		masterHTML += "<h3> Total storage size (week): {} mb</h3>".format(round(totalSize, 2))
		masterHTML += "<h3> Total cost (week): ${}</h3> <p>".format(round(costPerWeeek, 2))
		masterHTML += "{}   </body></html>".format(html.html)

		if not debug:
			if creditsUsedPerWeek >= int(parser['AGOL']['CREDITTHRESHOLD']):
				to_email = find_email(CM.users, user_name)
				email_wrapper(parser, user_name, to_email, masterHTML)
		else:
			logging.debug("DEBUG MODE: USER EMAIL")
			email_wrapper(parser, user_name, to_email_dbg, masterHTML)

	
	adminHTML = "<html>{}<body><h2>{} org credit consumption for week of {}</h2>".format(utils.style, CM.urlKey, datetime.date.today().strftime("%b-%d-%Y"))
	adminHTML += "<h3>Finished parsing total {} users. {} with FS and counted {} items</h3>".format(len(CM.users), len(CM.itms.items()), total_items)
	adminHTML += "<h4>Total FS Size  {} mb</h4>".format(round(all_fs_size, 2))
	adminHTML += "<h4>Total FS hosted credits used: {} (week)</h4>".format(round(all_credits_month /4, 2))
	
	adminHTML += "<h4>Geocode Credits Used</h4> <ul>{}</ul>".format(utils.parse_credit(CM.geocode_credits))
	adminHTML += "<h4>Geoenrich Credits Used</h4> <ul>{}</ul>".format(utils.parse_credit(CM.geoenrich_credits))  
	adminHTML += "<h4>Spatial Analyst Credits Used</h4> <ul>{}</ul>".format(utils.parse_credit(CM.spatialanalysis_credits))  

	adminTable = utils.html_table(admin_user_list_items)
	adminHTML += "<h4>Feature Service Usage</h4> {}".format(adminTable.html)
	adminHTML += "</body></html>"
	
	if not debug:
		admin_emails = [find_email(CM.users, a) for a in CM.admins]
	else:
		logging.debug("DEBUG MODE: ADMIN EMAIL")
		admin_emails = [to_email_dbg]
	logging.info("Sending admin emails to: {}".format(admin_emails))
	for e in admin_emails:
		email_wrapper(parser, None, e, adminHTML)

	logging.info("Finished parsing total {} users. {} with FS and counted {} items".format(len(CM.users), len(CM.itms.items()), total_items))