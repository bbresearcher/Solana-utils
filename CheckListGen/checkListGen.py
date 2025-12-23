#I DO NOT WARRANTY THIS CODE TO BE BUG FREE OR TO BE FIT FOR PURPOSE, RUNNING checkListGen AGAINST A PROJECT DOES NOT GUARANTEE THAT THE PROJECT IS SECURE AND/OR BUG FREE
from subprocess import PIPE,Popen,TimeoutExpired
import random
import os
import glob
import json
import re

def find_occurrences(text_string, char_to_find):
    """
    Finds occurrences of a character/substring in a string based on the length of char_to_find.

    If char_to_find is a single character, it finds occurrences that are not immediately repeated.
    If char_to_find is a multi-character string, it finds all starting indices of that substring.

    Args:
        text_string (str): The string to search within.
        char_to_find (str): The character(s) or substring to find.

    Returns:
        list: A list of indices where the character/substring is found according to the rules.
              Returns an empty list if no such occurrences are found.
    """
    if not isinstance(text_string, str) or not isinstance(char_to_find, str) or not char_to_find:
        raise ValueError("Both inputs must be strings, and 'char_to_find' cannot be empty.")

    found_indices = []
    n = len(text_string)
    len_char_to_find = len(char_to_find)

    if len_char_to_find == 1:
        # Original logic for single, unrepeated characters
        for i in range(n):
            if text_string[i] == char_to_find:
                is_prev_char_same = (i > 0 and text_string[i - 1] == char_to_find)
                is_next_char_same = (i < n - 1 and text_string[i + 1] == char_to_find)

                if not is_prev_char_same and not is_next_char_same:
                    found_indices.append(i)
                elif i == 0 and not is_next_char_same:
                    found_indices.append(i)
                elif i == n - 1 and not is_prev_char_same:
                    found_indices.append(i)
    else:
        # Logic for multi-character substrings
        # Using a loop with find to get all occurrences, not just the first
        start_index = 0
        while True:
            index = text_string.find(char_to_find, start_index)
            if index == -1:
                break  # Substring not found
            found_indices.append(index)
            start_index = index + len_char_to_find # Move past the found substring to search for next
            if start_index >= n: # Prevent infinite loop if char_to_find is empty (already checked) or goes past end
                break

    return found_indices

def runcheckListGen(project_dir,rules_dir,ignore_dirs=None):
    if ignore_dirs is None:
        ignore_dirs = []
    # Used for progress output
    print("---START--------------------------------------------------------------------\n")
    # Used for report output
    MarkdownString = "# checkListGen Report\n"
    print("[+] Running checkListGen against directory: ",project_dir)
    MarkdownString = MarkdownString + "- Running checkListGen against directory: " + project_dir + "\n"
    print("\n")
    print("[+] Rules templates directory set as : ",rules_dir)
    MarkdownString = MarkdownString + "- Rules templates directory set as : " + rules_dir + "\n"
    print("\n")
    try:
        # First import all templates to minimise IO
        # Rules are stored in the rules array
        rules = []
        rulecheckfinds = ""
        for jsonfile in os.listdir(rules_dir):
            with open(rules_dir + "/" + jsonfile, 'r', encoding="utf-8") as rulefile:
                ruleEntry = rulefile.read()
                rule = json.loads(ruleEntry)
                rules.append(rule)
        
        # Dictionary to store account usage across all contexts
        account_usage_map = {}
        
        # Now check for files that implement the Circuit trait    
        accountsList = "## Rust files found:\n"
        # Walk all directories and subdirectories from the main folder which was set in project_dir
        for root,dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                # Only read files ending in ".rs"
                if file.endswith(".rs"):
                    hasAccounts = False
                    foundObj = True
                    with open(os.path.join(root,file), 'r', encoding="utf-8") as rustfile:
                        rustcode = rustfile.read()
                        # For now just check for text as below which should find "#[derive(Accounts)]"
                        if rustcode.find("#[derive(Accounts)]") > 0:
                            accountsList = accountsList + "   [^] " + file + "\n"
                            hasAccounts = True
                        rustfile.close()

                        if hasAccounts:
                            # Parse the file to extract context names and their accounts
                            current_context = None
                            in_context = False
                            context_accounts = []
                            
                            with open(os.path.join(root,file), 'r', encoding="utf-8") as rustfile:
                                for rustLine in rustfile:
                                    # Detect new context struct
                                    if "#[derive(Accounts)]" in rustLine:
                                        in_context = True
                                        continue
                                    
                                    if in_context and re.search(r'\bpub\s+struct\s+(\w+)', rustLine):
                                        match = re.search(r'pub\s+struct\s+(\w+)', rustLine)
                                        current_context = match.group(1)
                                        continue
                                    
                                    if in_context and "}" in rustLine and current_context:
                                        # End of context struct
                                        in_context = False
                                        current_context = None
                                        continue
                                    
                                    # Parse account fields within context
                                    if in_context and current_context and ":" in rustLine and "pub" in rustLine:
                                        # Extract account name
                                        account_match = re.search(r'pub\s+(\w+)\s*:', rustLine)
                                        if account_match:
                                            account_name = account_match.group(1)
                                            
                                            # Initialize account in map if not exists
                                            if account_name not in account_usage_map:
                                                account_usage_map[account_name] = {
                                                    'contexts': {},
                                                    'type': None
                                                }
                                            
                                            # Extract type
                                            type_match = re.search(r':\s*(.+?)(?:,|$)', rustLine)
                                            if type_match:
                                                account_type = type_match.group(1).strip()
                                                if not account_usage_map[account_name]['type']:
                                                    account_usage_map[account_name]['type'] = account_type
                                            
                                            # Initialize this context usage
                                            if current_context not in account_usage_map[account_name]['contexts']:
                                                account_usage_map[account_name]['contexts'][current_context] = {
                                                    'file': os.path.join(root, file),
                                                    'attributes': []
                                                }
                                
                            # Now parse again to get attributes for each account
                            with open(os.path.join(root,file), 'r', encoding="utf-8") as rustfile:
                                current_context = None
                                in_context = False
                                current_account = None
                                collecting_attributes = False
                                current_attributes = []
                                open_brackets = 0
                                
                                for rustLine in rustfile:
                                    # Detect new context struct
                                    if "#[derive(Accounts)]" in rustLine:
                                        in_context = True
                                        continue
                                    
                                    if in_context and re.search(r'\bpub\s+struct\s+(\w+)', rustLine):
                                        match = re.search(r'pub\s+struct\s+(\w+)', rustLine)
                                        current_context = match.group(1)
                                        continue
                                    
                                    if in_context and "}" in rustLine and not collecting_attributes:
                                        # End of context struct
                                        in_context = False
                                        current_context = None
                                        continue
                                    
                                    # Detect #[account( attributes
                                    if in_context and "#[account(" in rustLine:
                                        collecting_attributes = True
                                        # Extract attributes from this line
                                        attr_text = rustLine.replace("#[account(", "").replace(")]", "").strip()
                                        if attr_text and attr_text != "":
                                            current_attributes.append(attr_text)
                                        
                                        # Check if attribute closes on same line
                                        if ")]" in rustLine:
                                            collecting_attributes = False
                                            # Next line should be the account
                                        elif "]" not in rustLine:
                                            # Multi-line attribute
                                            open_brackets = 1
                                        continue
                                    
                                    # Continue collecting multi-line attributes
                                    if collecting_attributes and current_context:
                                        if ")]" in rustLine or ("]" in rustLine and open_brackets == 1):
                                            # End of attributes
                                            attr_text = rustLine.replace(")]", "").replace("]", "").strip()
                                            if attr_text and attr_text != "":
                                                current_attributes.append(attr_text)
                                            collecting_attributes = False
                                            open_brackets = 0
                                            # Next line should be the account
                                        else:
                                            attr_text = rustLine.strip()
                                            if attr_text and attr_text != "":
                                                current_attributes.append(attr_text)
                                        continue
                                    
                                    # Parse account field that follows attributes
                                    if in_context and current_context and ":" in rustLine and "pub" in rustLine:
                                        account_match = re.search(r'pub\s+(\w+)\s*:', rustLine)
                                        if account_match:
                                            account_name = account_match.group(1)
                                            
                                            # Store the attributes for this account in this context
                                            if current_attributes and account_name in account_usage_map:
                                                if current_context in account_usage_map[account_name]['contexts']:
                                                    account_usage_map[account_name]['contexts'][current_context]['attributes'] = current_attributes.copy()
                                            
                                            # Reset for next account
                                            current_attributes = []

                        if hasAccounts:
                            accountsList = accountsList + "### File: " + os.path.join(root,file) + "\n "
                            strObj = ""
                            strAddInstr = ""
                            strAttributes = ""
                            with open(os.path.join(root,file), 'r', encoding="utf-8") as rustfile:
                                foundObj = False
                                attributesfound = False
                                openAttrib = 0
                                
                                for rustLine in rustfile:
                                    isInstruction = False
                                    if rustLine.find("[derive(Accounts)]") > 0:
                                        foundObj = True
                                    if foundObj:
                                        if rustLine.find("}") > 0:
                                            foundObj = False
                                        if rustLine.find("[instruction(") > 0:
                                            strAddInstr = "Struct has instuction inputs of : " + rustLine.replace("#","").replace("\n","")
                                            isInstruction = True
                                        if re.search(r'\b{}\b'.format("pub struct"),rustLine):
                                            strObj = strObj + "---\n🔷 **#: Account Object found: " + rustLine.split("struct",1)[1].split("<",1)[0].strip() + "**\n\n"
                                            if len(strAddInstr) > 0:
                                                strObj = strObj + "➡️  *" + strAddInstr + "* \n\n"
                                                strAddInstr = "" 
                                        if rustLine.find("[") > 0 and rustLine.find("]") < 0 and attributesfound == True:
                                            openAttrib = openAttrib + 1  
                                        if attributesfound:
                                            if openAttrib > 0:
                                                strTmp = rustLine.replace("]","").replace(")","").strip()
                                            else:
                                                if rustLine.find("]") > 0:
                                                    if rustLine.find("[") > 0 and rustLine.find("]") > 0:
                                                        strTmp = rustLine.strip()
                                                    else:
                                                        strTmp = rustLine.replace("]","").replace(")","").strip()
                                                else:
                                                    strTmp = rustLine.strip()
                                            if len(strTmp)> 0:
                                                strAttributes = strAttributes +  "- " + strTmp  + "\n"
                                        if rustLine.find("#[account(") > 0:
                                            strObj = strObj + "📋 Anchor account member below has attributes: \n"
                                            attributesfound = True
                                            strTmp = rustLine.replace("#[account(","").replace(")","").replace("]","").strip()
                                            if len(strTmp)> 0:
                                                strAttributes = strAttributes+ "- " + strTmp + "\n"  
                                            if rustLine.find("]") > 0:
                                                attributesfound = False 
                                                strObj = strObj + strAttributes + "\n"
                                        if rustLine.find("]") > 0 and rustLine.find("[") < 0 and attributesfound == True:
                                            if openAttrib > 0:
                                                openAttrib = openAttrib - 1
                                            else:
                                                attributesfound = False
                                                strTmp = rustLine.replace(")]","").strip()
                                                if len(strTmp)> 0:
                                                    strAttributes = strAttributes+ "- " + strTmp + "\n"
                                                strObj = strObj + strAttributes + "\n"
                                                strAttributes = ""                                   
                                            
                                        if rustLine.find(":") > 0 and attributesfound == False and isInstruction == False:
                                            strObj = strObj + "🔴 **[STRUCT FIELD:] " + rustLine.split(":",1)[0].replace("pub ", "").strip() + " of type " + rustLine.split(":",1)[1].replace("\n","").strip() + "**\n\n"

                            accountsList = accountsList + strObj
                            strObj = ""
                            strAddInstr = ""
                            
                    # Run template-based checks on all .rs files
                    with open(os.path.join(root,file), 'r', encoding="utf-8") as rustfile:
                        rustcode = rustfile.read()
                        rustfile.close()
                    
                    # Now loop through the rules array and check the "match" value against the code 
                    # retrieved from reading the source file
                    for rule in rules:
                        intfound = 0
                        for strmatch in rule["match"]:
                            #if rustcode.find(strmatch) > 0:
                            if len(find_occurrences(rustcode,strmatch)) > 0:
                                # The counter makes sure it only lists the file once 
                                # and not for each match in a file
                                if intfound == 0:
                                    intfound = 1
                                    rulecheckfinds = rulecheckfinds + "### File: " + os.path.join(root,file) + "\n   #: Match found on : " + strmatch + "\n   #: " + rule["description"] + "\n\n"
                                    # setup the file path
                                    filepath = os.path.join(root,file)
                                    # Use Popen to open grep the "match" value in the file
                                    # and capture the output
                                    with Popen("grep -n -C 1 '" + strmatch + "' " + filepath + " -rIs",shell=True,stdout=PIPE) as proc:
                                        try:
                                            out, errs = proc.communicate(timeout=15)
                                        except TimeoutExpired:
                                            proc.kill()
                                            out, errs = proc.communicate()
                                        bashOutput = out.decode()
                                    # String to concatenate all match finds
                                    rulecheckfinds = rulecheckfinds + "```\n" + bashOutput + "\n```\n"
        
        # Generate the account usage checklist
        accountChecklist = "\n\n## 📋 ACCOUNT USAGE CHECKLIST\n\n"
        accountChecklist += "This section lists all accounts found in the codebase and shows which instructions/contexts use them and with what attributes.\n\n"
        
        if account_usage_map:
            # Sort accounts alphabetically
            for account_name in sorted(account_usage_map.keys()):
                account_info = account_usage_map[account_name]
                accountChecklist += f"### 🔑 Account: `{account_name}`\n\n"
                
                if account_info['type']:
                    accountChecklist += f"**Type:** `{account_info['type']}`\n\n"
                
                if account_info['contexts']:
                    accountChecklist += f"**Used in {len(account_info['contexts'])} instruction(s)/context(s):**\n\n"
                    
                    for context_name in sorted(account_info['contexts'].keys()):
                        context_data = account_info['contexts'][context_name]
                        accountChecklist += f"- **Context/Instruction: `{context_name}`**\n"
                        accountChecklist += f"  - File: `{context_data['file']}`\n"
                        
                        if context_data['attributes']:
                            accountChecklist += "  - **Attributes:**\n"
                            for attr in context_data['attributes']:
                                # Parse common attributes for better display
                                attr_clean = attr.strip().rstrip(',')
                                if 'mut' in attr_clean:
                                    accountChecklist += f"    - 🔄 **MUTABLE** ({attr_clean})\n"
                                elif 'signer' in attr_clean.lower():
                                    accountChecklist += f"    - ✍️ **SIGNER** ({attr_clean})\n"
                                elif 'init' in attr_clean:
                                    accountChecklist += f"    - 🆕 **INIT** ({attr_clean})\n"
                                elif 'constraint' in attr_clean:
                                    accountChecklist += f"    - ⚠️ **CONSTRAINT** ({attr_clean})\n"
                                else:
                                    accountChecklist += f"    - {attr_clean}\n"
                        else:
                            accountChecklist += "  - **Attributes:** None specified\n"
                        
                        accountChecklist += "\n"
                else:
                    accountChecklist += "**Not used in any context**\n\n"
                
                accountChecklist += "---\n\n"
        else:
            accountChecklist += "*No accounts found in the analyzed files.*\n\n"
                        
        print(accountsList)
        print(accountChecklist)
        print("## Rule checks returned the list of code to check below:\n") 
        rulecheckfinds = "## Rule checks returned the list of code to check below:\n" + rulecheckfinds
        print(rulecheckfinds)
        print("---END----------------------------------------------------------------------")
        # Setup final string to write out to report
        MarkdownString = MarkdownString + accountsList + accountChecklist + rulecheckfinds        #Write out the markdown into the report file
        f = open("checkList.md", "w")
        f.write(MarkdownString)
        f.close()
    except Exception as e:
        print("[#### ] checkListGen ran into an exception : ",e)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", help="The project directory")
    parser.add_argument("rules_dir", help="The directory which has the JSON rules templates to check against")
    parser.add_argument("--ignore-dirs", help="Comma separated list of directory names to ignore", default="")
    args = parser.parse_args()
    ignore_dirs = [d.strip() for d in args.ignore_dirs.split(",") if d.strip()] if args.ignore_dirs else []
    runcheckListGen(args.project_dir, args.rules_dir, ignore_dirs)

main()
