# AGOL Credit Reporter

This workflow authenticates against ArcGIS Online using an administrative connection. Once authenticated, a query is performed to find all hosted feature services. A calculation is performed to determine the size and credit cost per user. Finally, an email is sent to the user(s) indicating how many credits they've spent through hosting and an email sent to the Organization's administrators.

The scripts have been designed to run as an Azure Function App. They also make use of the o365 Python Module that calls the Microsoft Graph API, sending emails through your Office 365 account. These scripts can be modified to run on-demand, in your local environment, however they have been designed to run at as a TimerTrigger app, executing on a defined interval.

Setup instructions below.

## Technology

- Python 3.7+
- Requests (Python module)
- O365 (Python module)
- Azure Subscription
- Office 365 email account
- ArcGIS Online Organization (requires an administrator account)

## Setup

These instructions assume you're using Visual Studio Code as your development environment. __Caution__: Setting up and getting o366 package to work (step 7) can be a flakey and frustrating process which will cause headaches. The development pattern used to load the token from the file seems very fragile and more often than not, simply doesn't work as you'll be prompted to complete the copy-paste authorization step. In a deployed function app, this is not possible. I've found that once you get the token created and working locally, publish your app. Do not do anything else with the token workflow (updating permissions, trying it from another workflow, etc). Once it works, just get it published.

1. Install the Azure Functions extension into VS Code from the Marketplace
2. Create a new Azure Function app. Use the [Quickstart](https://docs.microsoft.com/en-us/azure/azure-functions/functions-create-first-function-vs-code?pivots=programming-language-python) to get started. Make sure you choose `TimerTrigger` instead of the HTTPTrigger.
3. After your environment is setup, download the code from this repository.
4. Copy the relevant files into the Function app you created (_init_.py, config.ini, utils.py). You'll need the _setup_O365_email.py, just not as part of the function app.
5. Update the config.ini file. 
  * Supply the credentials of an AGOL Administrator
  * The script assumes it will be run once a week. Set a credit threshold for when people will be emailed. Default value is 10 (anyone using more than 10 will receive an email)
  * Follow the Authentication Steps very closely from the [O365 setup documentation](https://pypi.org/project/O365/). You will probably be using a personal account, and as such, make sure to follow the _on behalf of a user_, or _delegated permissions_. These steps will produce a Client ID and Secret. Update these values into the INI file.
6. Ensure you have the required Python modules installed:
  * `pip install o365`
  * `pip install requests`
7. Run the `_setup_O365_email.py` script to generate the `o365_token.txt` file. Copy this file into the same directory as step 4.
8. Test your application locally. Change the _schedule_ of the `function.json` file to something like run everyone 1 minute: `0 */1 * * * *`. You may receive a lot of emails if you have a lot of users who have exceeded the credit threshold.
9. After you've got the script running properly, change the _schedule_ of the `function.json` to your required interval. The value of `0 0 7 * * Mon` will run every Monday at 7am.
10. Update the `config.ini` _SETUP_ > _DEBUG_ value to False (Upper-case F)
11. Publish the Function App to Azure. The Quickstart referenced in 2) explains this process in more detail.


## Notes

Protect the contents of your config.ini file! This file has the username and password of an administration account to your ArcGIS Online Organization. The file also has the necessary keys that could allow someone to use your email account to send emails on your behalf. (If you've granted Read or other GRAPH permissions, than the keys could possibly be used to do more than just send emails.) ArcGIS.com does support OAUTH and Client/Secret workflows. However, the app you creat and keys supplied are NOT administrator keys. You cannot use this more secure workflow and leverage the administrative endpoints that this code requires.

Be thoughtful about the credit threshold and how often you run the script. Too many emails and your users will delete/ignore. If you want your users to proactively keep their account clean of un-necessary files, you shouldn't spam them.

## To-Do

Remove keys/usernames/passwords from the INI and implement a more secure Azure container for these items.
