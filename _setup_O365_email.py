'''
  This script must be run on its own, outside the Azure Function app and the environment before you deploy.
  After you've obtained an AppID and Secret from Azure's GRAPH API, plug them and your email address in.
  Run the script. It should create a file   o365_token.txt   in the same directory as this script
  This file will have the access token inside that your Azure Function app will need to authenticate with Graph
  and send emails. 
  See the detailed o365 library help or further instructions in the readme.
'''
from O365 import Account, FileSystemTokenBackend
from pathlib import Path

appID = "Your App ID from Azure"
c_secret = "Your client secret from Azure"
from_email = "from@your.email.address"
to_email = "your@email.address"	

token_backend = FileSystemTokenBackend(token_path=Path(__file__).parent, token_filename='o365_token.txt')

credentials = (appID, c_secret)
account = Account(credentials, token_backend=token_backend)

if not account.authenticate():
	account.authenticate()
	print("o365 emailer is not authenticated. Requires manual investigation.")

example_mailbox = account.mailbox(resource=from_email)
m = example_mailbox.new_message()
m.to.add(to_email)
m.subject = "This is a test setup email"
m.body = "This is the body of a test setup email"
m.send()