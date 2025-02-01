import requests
import json
import os
import pyfiglet
import curses
import subprocess

# Replace with your actual LeakIX API key
API_KEY = 'maYqHUYfmP17N5RsNhQLgcprt0SpP4_w9IcXqCjuP3yvArwJ'

# List of plugins to search for
PLUGINS = [
    "ApacheActiveMQ",
    "ApacheOFBizPlugin",
    "ApacheStatusPlugin",
    "BitbucketPlugin",
    "CentosWebPanelPlugin",
    "CheckMkPlugin",
    "CheckpointGwPlugin",
    "CiscoRV",
    "CitrixADCPlugin",
    "CloudPanelPlugin",
    "ConfigJsonHttp",
    "ConfluenceVersionIssue",
    "ConnectWiseScreenConnect",
    "Consul",
    "CouchDbOpenPlugin",
    "CrushFTPPlugin",
    "CyberPanelPlugin",
    "DeadMon",
    "DockerRegistryHttpPlugin",
    "DotDsStoreOpenPlugin",
    "DotEnvConfigPlugin",
    "ElasticSearchOpenPlugin",
    "EsxVersionPlugin",
    "ExchangeVersion",
    "FortiGatePlugin",
    "FortiOSPlugin",
    "GenericDvrPlugin",
    "GitConfigHttpPlugin",
    "GitlabPlugin",
    "GoAnywhereMFT",
    "GrafanaOpenPlugin",
    "HiSiliconDVR",
    "HttpNTLM",
    "IOSEXPlugin",
    "IvantiConnectSecure",
    "JenkinsOpenPlugin",
    "JenkinsVersionPlugin",
    "JiraPlugin",
    "JunosJWebPlugin",
    "KafkaOpenPlugin",
    "KerioControlPlugin",
    "LaravelTelescopeHttpPlugin",
    "Log4JOpportunistic",
    "MetabaseHttpPlugin",
    "MinioPlugin",
    "MirthPlugin",
    "MitelMiCollabPlugin",
    "MobileIronCorePlugin",
    "MobileIronSentryPlugin",
    "MongoOpenPlugin",
    "MoodlePlugin",
    "MysqlOpenPlugin",
    "NexusRepoPlugin",
    "OpenEdgePlugin",
    "PaloAltoPlugin",
    "PaperCutPlugin",
    "PhpCgiRcePlugin",
    "PhpInfoHttpPlugin",
    "PhpStdinPlugin",
    "ProxyOpenPlugin",
    "PulseConnectPlugin",
    "QnapVersion",
    "RedisOpenPlugin",
    "SharePointPlugin",
    "SmbPlugin",
    "SolrOpenPlugin",
    "SolrVersionPlugin",
    "SonarQubePlugin",
    "SonicWallGMSPlugin",
    "SonicWallSMAPlugin",
    "SophosPlugin",
    "SplunkPlugin",
    "SpringBootActuatorPlugin",
    "SshRegresshionPlugin",
    "SymfonyProfilerPlugin",
    "SymfonyVerbosePlugin",
    "SysAidPlugin",
    "TeamCityPlugin",
    "TraversalHttpPlugin",
    "VCenterVersionPlugin",
    "veeaml9",
    "VeeamPlugin",
    "ViciboxPlugin",
    "VinChinBackupPlugin",
    "VMWareCloudDirector",
    "VsCodeSFTPPlugin",
    "WpUserEnumHttp",
    "WsFTPPlugin",
    "Wso2Plugin",
    "YiiDebugPlugin",
    "ZimbraPlugin",
    "ZookeeperOpenPlugin",
    "ZyxelVersion"
]

##############################################
# Tree Viewer Classes and Functions
##############################################

class TreeNode:
    def __init__(self, key, value=None, depth=0, parent=None):
        self.key = key          # The key or label for this node
        self.value = value      # For leaves, store the primitive value
        self.children = []      # List of child TreeNode objects
        self.expanded = False   # Whether this node is expanded (if it has children)
        self.depth = depth      # Depth in the tree (for indentation)
        self.parent = parent    # Parent node reference

    def is_leaf(self):
        return len(self.children) == 0

    def add_child(self, child):
        child.parent = self
        self.children.append(child)

def build_tree(data, key="root", depth=0, parent=None):
    """
    Recursively build a tree from JSON-like data.
    If data is a dict, each key becomes a child node.
    If data is a list, each item becomes a child node (labeled with its index).
    Otherwise, the node is a leaf containing the primitive value.
    """
    node = TreeNode(key, depth=depth, parent=parent)
    if isinstance(data, dict):
        for k, v in data.items():
            child = build_tree(v, key=str(k), depth=depth+1, parent=node)
            node.add_child(child)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            child = build_tree(item, key=f"[{i}]", depth=depth+1, parent=node)
            node.add_child(child)
    else:
        node.value = data
    return node

def flatten_tree(node):
    """Return a flat list of nodes that are visible (i.e. expanded nodes include their children)."""
    result = [node]
    if node.expanded:
        for child in node.children:
            result.extend(flatten_tree(child))
    return result

def render_tree_node(node, max_width):
    """Return a formatted string for a single node, limited to max_width characters."""
    indent = "  " * node.depth
    if not node.is_leaf():
        marker = "-" if node.expanded else "+"
    else:
        marker = " "
    if node.is_leaf():
        line = f"{indent}{marker} {node.key}: {node.value}"
    else:
        line = f"{indent}{marker} {node.key}"
    return line[:max_width-1]

def host_search_from_ip(stdscr, ip):
    if get_input(stdscr, f"Do you want to search this IP ({ip})? (y/n): ").lower() == 'y':
        result = fetch_host_results(ip)
        if result:
            tree = build_tree(result, key="Host Search Results")
            tree.expanded = True
            tree_viewer(stdscr, tree)
        else:
            max_y, max_x = stdscr.getmaxyx()
            message = "No host results found. Press any key to return."
            stdscr.addstr(max_y - 1, max_x - len(message), message, curses.color_pair(3))  # Green
            stdscr.getch()

def domain_search_from_host(stdscr, host):
    if get_input(stdscr, f"Do you want to search this domain ({host})? (y/n): ").lower() == 'y':
        result = fetch_domain_results(host)
        if result:
            tree = build_tree(result, key="Domain Search Results")
            tree.expanded = True
            tree_viewer(stdscr, tree)
        else:
            max_y, max_x = stdscr.getmaxyx()
            message = "No domain results found. Press any key to return."
            stdscr.addstr(max_y - 1, max_x - len(message), message, curses.color_pair(3))  # Green
            stdscr.getch()

def ensure_terminal_size(stdscr):
    min_height, min_width = 35, 100  # Example minimum dimensions
    max_y, max_x = stdscr.getmaxyx()
    
    if max_y < min_height or max_x < min_width:
        # Clear the screen and inform the user
        stdscr.clear()
        stdscr.addstr(0, 0, "Please resize your terminal window to at least:")
        stdscr.addstr(1, 0, f"Height: {min_height}")
        stdscr.addstr(2, 0, f"Width: {min_width}")
        stdscr.addstr(4, 0, "Press any key when ready...")
        stdscr.refresh()
        stdscr.getch()
        
        # You can't actually resize the terminal here, but you can wait for the user
        # to do it manually
        while True:
            max_y, max_x = stdscr.getmaxyx()
            if max_y >= min_height and max_x >= min_width:
                break
            stdscr.addstr(6, 0, "Still too small, please resize and press any key...")
            stdscr.refresh()
            stdscr.getch()

def tree_viewer(stdscr, root):
    current_index = 0
    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        visible_nodes = flatten_tree(root)
        stdscr.addstr(0, 0, "Tree Viewer (UP/DOWN: navigate, ENTER: action, S: save, Q: exit)", curses.color_pair(3))
        for i in range(1, max_y - 1):
            idx = current_index + i - 1
            if idx < len(visible_nodes):
                node = visible_nodes[idx]
                line = render_tree_node(node, max_x)
                if idx == current_index:
                    stdscr.attron(curses.color_pair(2))
                    stdscr.addstr(i, 0, line)
                    stdscr.attroff(curses.color_pair(2))
                else:
                    stdscr.addstr(i, 0, line)
        stdscr.refresh()
        key = stdscr.getch()
        if key == curses.KEY_UP and current_index > 0:
            current_index -= 1
        elif key == curses.KEY_DOWN and current_index < len(visible_nodes) - 1:
            current_index += 1
        elif key in [curses.KEY_ENTER, 10, 13]:
            node = visible_nodes[current_index]
            if node.is_leaf():
                if node.key == 'ip' and isinstance(node.value, str):
                    host_search_from_ip(stdscr, node.value)
                elif node.key == 'host' and isinstance(node.value, str):
                    domain_search_from_host(stdscr, node.value)
                elif node.key == 'summary':
                    # Look for 'event_source' on the same level as 'summary'
                    event_source_node = next((sibling for sibling in visible_nodes if sibling.key == 'event_source' and sibling.parent == node.parent), None)
                    if event_source_node and 'ElasticSearchOpenPlugin' in str(event_source_node.value):
                        # Find 'host' node on the same level
                        host_node = next((sibling for sibling in visible_nodes if sibling.key == 'host' and sibling.parent == node.parent), None)
                        if host_node:
                            host = host_node.value
                            if handle_elasticsearch_list(stdscr, host):
                                handle_elasticsearch_index_selection(stdscr, host)
            else:
                node.expanded = not node.expanded
        elif key in [ord('q'), ord('Q')]:
            break
        elif key in [ord('s'), ord('S')]:
            save_tree_to_file(stdscr, root)

def save_tree_to_file(stdscr, root):
    max_y, max_x = stdscr.getmaxyx()
    visible_nodes = flatten_tree(root)
    lines = [render_tree_node(node, max_x) for node in visible_nodes]
    output_str = "\n".join(lines)
    stdscr.clear()
    filename = get_input(stdscr, "Enter filename to save output (without extension): ")
    try:
        with open(f"{filename}.txt", "w", encoding="utf-8") as f:
            f.write(output_str)
        stdscr.addstr("\nOutput saved successfully. Press any key to return...", curses.color_pair(3))
    except Exception as e:
        stdscr.addstr(f"\nError saving file: {e}", curses.color_pair(4))
    stdscr.getch()

##############################################
# API Fetch Functions
##############################################

def fetch_search_results(query, scope, start_page=0, end_page=0):
    all_results = []
    for page in range(start_page, end_page + 1):
        url = f"https://leakix.net/search?q={query}&scope={scope}&page={page}"
        headers = {
            'Accept': 'application/json',
            'api-key': API_KEY
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            results = response.json()
            if not results:  # No more results to return
                break
            all_results.extend(results)
        except requests.RequestException as e:
            print(f"Error fetching page {page}: {e}")
            break
        # Rate limiting to avoid hitting API limits
        import time
        time.sleep(1)  # Sleep for 1 second between requests
    return all_results

def fetch_host_results(host):
    url = f"https://leakix.net/host/{host}"
    headers = {
        'Accept': 'application/json',
        'api-key': API_KEY
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result
    except requests.RequestException:
        return None

def fetch_domain_results(domain):
    url = f"https://leakix.net/domain/{domain}"
    headers = {
        'Accept': 'application/json',
        'api-key': API_KEY
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result
    except requests.RequestException:
        return None

##############################################
# Helper Function for User Input in Curses
##############################################

def get_input(stdscr, prompt):
    stdscr.addstr(prompt)
    stdscr.refresh()
    curses.echo()
    input_str = stdscr.getstr().decode('utf-8')
    curses.noecho()
    return input_str

##############################################
# Curses UI Functions for Each Search Option
##############################################

def plugin_menu(stdscr):
    current_index = 0
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Select a plugin (UP/DOWN: navigate, ENTER: select, Q to cancel):", curses.color_pair(3))
        max_y, max_x = stdscr.getmaxyx()
        visible_items = max_y - 4
        start = max(0, current_index - visible_items + 1) if current_index >= visible_items else 0
        for i, plugin in enumerate(PLUGINS[start:start+visible_items]):
            idx = start + i
            text = f"{idx+1}. {plugin}"[:max_x-1]
            if idx == current_index:
                stdscr.attron(curses.color_pair(2))
                stdscr.addstr(i+2, 2, text)
                stdscr.attroff(curses.color_pair(2))
            else:
                stdscr.addstr(i+2, 2, text)
        stdscr.refresh()
        key = stdscr.getch()
        if key == curses.KEY_UP and current_index > 0:
            current_index -= 1
        elif key == curses.KEY_DOWN and current_index < len(PLUGINS) - 1:
            current_index += 1
        elif key in [curses.KEY_ENTER, 10, 13]:
            return PLUGINS[current_index]
        elif key in [ord('q'), ord('Q')]:
            return None

def curses_search_by_plugin(stdscr):
    stdscr.clear()
    banner(stdscr)
    max_y, max_x = stdscr.getmaxyx()

    plugin = plugin_menu(stdscr)
    if plugin is None:
        return
    stdscr.clear()
    banner(stdscr)  # Redraw banner
    y = len(banner_text.split('\n')) + 1  # Start under the banner
    x = max_x // 2 - len(f"Searching for plugin: {plugin}") // 2  # Center the text
    stdscr.addstr(y, x, f"Searching for plugin: {plugin}", curses.color_pair(3))
    stdscr.refresh()
    query = f'+plugin:"{plugin}"'
    results = fetch_search_results(query, 'leak')
    if results:
        tree = build_tree(results, key="Results")
        tree.expanded = True
        tree_viewer(stdscr, tree)
    else:
        y += 2
        x = max_x // 2 - len("No results found.") // 2
        stdscr.addstr(y, x, "No results found.", curses.color_pair(4))
        stdscr.getch()

def curses_search_by_query(stdscr):
    stdscr.clear()
    banner(stdscr)
    max_y, max_x = stdscr.getmaxyx()
    
    banner_height = len(banner_text.split('\n'))
    y = banner_height + 1  # Start under the banner
    x = max_x // 2 - len("Search by Query") // 2  # Center horizontally
    stdscr.addstr(y, x, "Search by Query", curses.color_pair(3))
    stdscr.refresh()

    y += 2  # Move down for the next line
    scope_prompt = "Enter scope (leak/service): "
    x = max_x // 2 - len(scope_prompt) // 2
    scope = get_input(stdscr, f"\n{scope_prompt}")
    if scope not in ['leak', 'service']:
        x = max_x // 2 - len("Invalid scope. Press any key to return.") // 2
        stdscr.addstr(y + 1, x, "Invalid scope. Press any key to return.", curses.color_pair(4))
        stdscr.getch()
        return
    
    y += 2  # Move down for the next line
    query_prompt = "Enter search query: "
    x = max_x // 2 - len(query_prompt) // 2
    query = get_input(stdscr, f"\n{query_prompt}")
    if not query:
        x = max_x // 2 - len("No query provided. Press any key to return.") // 2
        stdscr.addstr(y + 1, x, "No query provided. Press any key to return.", curses.color_pair(4))
        stdscr.getch()
        return
    
    y += 2  # Move down for the next line
    start_page_prompt = "Enter starting page number: "
    x = max_x // 2 - len(start_page_prompt) // 2
    start_page = int(get_input(stdscr, f"\n{start_page_prompt}"))
    y += 2  # Move down for the next line
    end_page_prompt = "Enter ending page number: "
    x = max_x // 2 - len(end_page_prompt) // 2
    end_page = int(get_input(stdscr, f"\n{end_page_prompt}"))

    if start_page < 0 or end_page < start_page:
        x = max_x // 2 - len("Invalid page range. Press any key to return.") // 2
        stdscr.addstr(y + 1, x, "Invalid page range. Press any key to return.", curses.color_pair(4))
        stdscr.getch()
        return

    results = fetch_search_results(query, scope, start_page, end_page)
    if results:
        tree = build_tree(results, key="Results")
        tree.expanded = True
        tree_viewer(stdscr, tree)
    else:
        x = max_x // 2 - len("No results found. Press any key to return.") // 2
        stdscr.addstr(y + 1, x, "No results found. Press any key to return.", curses.color_pair(4))
        stdscr.getch()

def curses_search_by_host(stdscr):
    stdscr.clear()
    banner(stdscr)
    max_y, max_x = stdscr.getmaxyx()
    y = len(banner_text.split('\n')) + 1
    x = max_x // 2 - len("Search by Host") // 2
    stdscr.addstr(y, x, "Search by Host", curses.color_pair(3))
    stdscr.refresh()
    y += 2
    x = max_x // 2 - len("Enter IP address to search: ") // 2
    host = get_input(stdscr, f"\nEnter IP address to search: ")
    if not host:
        x = max_x // 2 - len("No IP provided. Press any key to return.") // 2
        stdscr.addstr(y + 1, x, "No IP provided. Press any key to return.", curses.color_pair(4))
        stdscr.getch()
        return
    result = fetch_host_results(host)
    if result:
        tree = build_tree(result, key="Results")
        tree.expanded = True
        tree_viewer(stdscr, tree)
    else:
        x = max_x // 2 - len("No results found. Press any key to return.") // 2
        stdscr.addstr(y + 1, x, "No results found. Press any key to return.", curses.color_pair(4))
        stdscr.getch()

def curses_search_by_domain(stdscr):
    stdscr.clear()
    banner(stdscr)
    max_y, max_x = stdscr.getmaxyx()
    y = len(banner_text.split('\n')) + 1
    x = max_x // 2 - len("Search by Domain") // 2
    stdscr.addstr(y, x, "Search by Domain", curses.color_pair(3))
    stdscr.refresh()
    y += 2
    x = max_x // 2 - len("Enter domain to search: ") // 2
    domain = get_input(stdscr, f"\nEnter domain to search: ")
    if not domain:
        x = max_x // 2 - len("No domain provided. Press any key to return.") // 2
        stdscr.addstr(y + 1, x, "No domain provided. Press any key to return.", curses.color_pair(4))
        stdscr.getch()
        return
    result = fetch_domain_results(domain)
    if result:
        tree = build_tree(result, key="Results")
        tree.expanded = True
        tree_viewer(stdscr, tree)
    else:
        x = max_x // 2 - len("No results found. Press any key to return.") // 2
        stdscr.addstr(y + 1, x, "No results found. Press any key to return.", curses.color_pair(4))
        stdscr.getch()

def curses_show_previous_results(stdscr):
    stdscr.clear()
    banner(stdscr)
    max_y, max_x = stdscr.getmaxyx()
    y = len(banner_text.split('\n')) + 1
    x = max_x // 2 - len("Previous Results") // 2
    stdscr.addstr(y, x, "Previous Results", curses.color_pair(3))
    y += 2
    x = max_x // 2 - len("Feature not implemented. Press any key to return.") // 2
    stdscr.addstr(y, x, "Feature not implemented. Press any key to return.", curses.color_pair(4))
    stdscr.getch()

def get_real_indices(host):
    # Determine protocol based on port assumption
    protocol = "http" if host.endswith(":80") else "https"
    
    try:
        # Construct command to list indices
        command = f'./estk --url={protocol}://{host} list'
        
        # Execute command; assuming 'estk' is in the same directory
        result = subprocess.run(command, capture_output=True, text=True, shell=False, timeout=30, check=True, cwd=os.path.dirname(__file__))
        
        indices = []
        for line in result.stdout.splitlines():
            if '(' in line:
                # Split the line to get index name and doc count
                parts = line.split('(')
                index_name = parts[0].strip()
                # Extract the number of docs from the part inside parentheses, 
                # assuming it's in the format 'X docs)'
                if len(parts) > 1:
                    doc_count = parts[1].split('docs')[0].strip()
                else:
                    doc_count = '0'  # Default to 0 if no count found
                indices.append((index_name, doc_count))
        
        return indices
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Command failed with return code {e.returncode}:\n{e.stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Command execution timed out.")
    except Exception as e:
        raise RuntimeError(f"An error occurred while fetching indices: {e}")

def handle_elasticsearch_list(stdscr, host):
    if get_input(stdscr, f"Do you want to list indexes for this host ({host})? (y/n): ").lower() == 'y':
        try:
            indices = get_real_indices(host)
            stdscr.clear()
            max_y, max_x = stdscr.getmaxyx()  # Define max_y and max_x here
            for i, (index_name, doc_count) in enumerate(indices):
                if i >= max_y - 1:  # Now max_y is defined
                    break
                stdscr.addstr(i, 0, f"{index_name} ({doc_count} docs)\n")
            stdscr.refresh()
            stdscr.getch()
            return True
        except RuntimeError as e:
            stdscr.addstr(f"Error: {str(e)}", curses.color_pair(4))
            stdscr.refresh()
            stdscr.getch()
            return False

def handle_elasticsearch_index_selection(stdscr, host):
    try:
        indices = get_real_indices(host)
    except RuntimeError as e:
        stdscr.addstr(f"Error fetching indices: {e}", curses.color_pair(4))
        stdscr.getch()
        return

    current_selection = 0
    while True:
        try:
            stdscr.clear()
            max_y, max_x = stdscr.getmaxyx()  # Define max_y and max_x here
            stdscr.addstr(0, 0, "Select an index (UP/DOWN: navigate, ENTER: select, Q: quit):", curses.color_pair(3))
            for i, (index_name, doc_count) in enumerate(indices):
                if i + 2 >= max_y:  # +2 because we start at line 2 for content
                    break
                if i == current_selection:
                    stdscr.attron(curses.color_pair(2))
                    stdscr.addstr(i + 2, 0, f"> {index_name} ({doc_count} docs)")
                    stdscr.attroff(curses.color_pair(2))
                else:
                    stdscr.addstr(i + 2, 0, f"  {index_name} ({doc_count} docs)")
            stdscr.refresh()
            key = stdscr.getch()
            if key == curses.KEY_UP and current_selection > 0:
                current_selection -= 1
            elif key == curses.KEY_DOWN and current_selection < len(indices) - 1:
                current_selection += 1
            elif key in [curses.KEY_ENTER, 10, 13]:
                selected_index, _ = indices[current_selection]
                protocol = "http" if host.endswith(":80") else "https"
                
                command = f'./estk --url={protocol}://{host} dump -i "{selected_index}"'
                
                try:
                    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, text=True, cwd=os.path.dirname(__file__))
                    
                    output_lines = []
                    for i, line in enumerate(iter(process.stdout.readline, '')):
                        if i >= 20:
                            process.terminate()
                            break
                        output_lines.append(line.rstrip('\n'))
                    
                    output = "\n".join(output_lines)
                    if process.poll() is None:
                        process.communicate()
                    if i >= 20:
                        output += "\n...\n(Output truncated after 20 lines)"
                    
                    stdscr.clear()
                    stdscr.addstr(0, 0, f"Output for index {selected_index}:\n{output}", curses.color_pair(1))
                    stdscr.refresh()
                    stdscr.getch()
                except subprocess.TimeoutExpired:
                    stdscr.addstr(0, 0, "Command execution timed out.", curses.color_pair(4))
                except subprocess.CalledProcessError as e:
                    stdscr.addstr(0, 0, f"Command execution failed with error: {e}", curses.color_pair(4))
                except Exception as e:
                    stdscr.addstr(0, 0, f"An error occurred: {e}", curses.color_pair(4))
                
                stdscr.getch()
                break
            elif key in [ord('q'), ord('Q')]:
                break
        except Exception as e:
            print(f"Error in handle_elasticsearch_index_selection: {e}")
            raise  # Re-raise the exception for full trace

##############################################
# Main Curses Application Loop
##############################################

banner_text = '''
oo_______________________oo________ooooo____________________________________
oo_______ooooo___ooooo___oo_______oo___oo__ooooo___ooooo___ooooo_____ooooo__
oo______oo___oo_oo___oo_oooo_______oo_____oo___oo_oo___oo_oo___oo____o___oo_
oo______oo___oo_oo___oo__oo__________oo___oo______oo___oo_oo___oo___oo___oo_
oo______oo___oo_oo___oo__oo__o____oo___oo_oo______oo___oo_oo___oo___oo___oo_
ooooooo__ooooo___ooooo____ooo______ooooo___ooooo___ooooo___ooooo__o_ooooo___
__________________________________________________________________oooo______
'''

def banner(stdscr):
    lines = banner_text.strip().split('\n')
    
    # Get terminal size
    max_y, max_x = stdscr.getmaxyx()
    
    # Place banner at the top center of the screen
    for i, line in enumerate(lines):
        x = max_x // 2 - len(line) // 2
        if x >= 0:  # Ensure we don't try to print off-screen
            for char in line:
                if char == 'o' or char == 'O':
                    stdscr.addch(i, x, char, curses.color_pair(3))  # Green for 'o'
                elif char == '_':
                    stdscr.addch(i, x, char, curses.color_pair(4))  # Red for '_'
                else:
                    stdscr.addch(i, x, char)
                x += 1  # Move to next character position

def main_curses(stdscr):
    # Check and ensure terminal size
    ensure_terminal_size(stdscr)
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    stdscr.scrollok(True)
    # Define color pairs
    curses.init_pair(1, curses.COLOR_WHITE, -1)              # Default text
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)  # Highlighted menu option
    curses.init_pair(3, curses.COLOR_GREEN, -1)               # Green for 'o'
    curses.init_pair(4, curses.COLOR_RED, -1)                 # Red for '_'
    curses.init_pair(5, curses.COLOR_YELLOW, -1)              # Prompts
    
    # Main menu options
    menu_options = [
        "Search by Plugin",
        "Search by Query",
        "Search by Host",
        "Search by Domain",
        "See Previous Results",
        "Exit"
    ]
    current_option = 0

    while True:
        stdscr.clear()
        # Display the banner at the top each time
        banner(stdscr)
        
        max_y, max_x = stdscr.getmaxyx()
        start_y = len(banner_text.split('\n')) + 2  # Start menu below banner

        for idx, option in enumerate(menu_options):
            # Center each menu item horizontally
            x = max_x // 2 - len(option) // 2
            y = start_y + idx
            text = option[:max_x-1]
            if idx == current_option:
                stdscr.attron(curses.color_pair(2))
                stdscr.addstr(y, x, text)
                stdscr.attroff(curses.color_pair(2))
            else:
                stdscr.addstr(y, x, text)
        
        # Center the footer
        footer = "Use UP/DOWN arrows to navigate, ENTER to select, Q to quit"
        x_footer = max_x // 2 - len(footer) // 2
        stdscr.addstr(max_y - 1, x_footer, footer, curses.color_pair(1))
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_UP and current_option > 0:
            current_option -= 1
        elif key == curses.KEY_DOWN and current_option < len(menu_options) - 1:
            current_option += 1
        elif key in [curses.KEY_ENTER, 10, 13]:
            if current_option == 0:
                curses_search_by_plugin(stdscr)
            elif current_option == 1:
                curses_search_by_query(stdscr)
            elif current_option == 2:
                curses_search_by_host(stdscr)
            elif current_option == 3:
                curses_search_by_domain(stdscr)
            elif current_option == 4:
                curses_show_previous_results(stdscr)
            elif current_option == 5:
                break
        elif key in [ord('q'), ord('Q')]:
            break

if __name__ == "__main__":
    curses.wrapper(main_curses)
    