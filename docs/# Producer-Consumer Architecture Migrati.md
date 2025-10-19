# Producer-Consumer Architecture Integration Plan

## Overview
Integrate a producer-consumer pattern into the action server using RCC subprocess calls. **The action server remains the orchestrator** - it will call the LinkedIn bot producer-consumer workflows and report on their output.

## Current Flow
- **Search Action**: Searches for linked jobs, enriches data with OpenAI GPT-5-nano, answers application form questions based on user profile
- **Apply Action**: Uses run ID to apply for all searched/answered applications

## New Architecture
**Action Server as Orchestrator**: The action server will invoke producer-consumer workflows via RCC subprocess calls and monitor their progress, collecting outputs and reporting results.

### Phase 1: Local File Adapter (Simple Implementation)
Start with Robocorp's local File Adapter for proof of concept.

### Phase 2: Custom Backend Integration
Build custom adapter to connect with:
- Celery Beat
- RabbitMQ
- Redis
- PostgreSQL (optional)

### Producer-Consumer Workflows
**Called by Action Server via RCC subprocess**

#### Workflow 1: Search & AI Processing
- **search_producer**: Parses input (search queries/CSV/Excel) and creates work items in database
- **ai_consumer**: Processes work items, performs OpenAI enrichment and answer generation, outputs run ID
- **Action Server**: Monitors progress, collects run ID output, reports status back to caller

#### Workflow 2: Application Submission
- **apply_producer**: Queries database for completed work items using run ID
- **apply_consumer**: Submits applications for processed items
- **Action Server**: Monitors application progress, collects results, reports completion status

## Input Methods
- List of search queries
- CSV file
- Excel file

## Scaling Strategy
1. Test with local File Adapter (action server calls RCC subprocess)
2. Implement custom job queue backend (action server orchestrates queue operations)
3. Scale to individual Docker workers (action server monitors distributed workers)
4. Create custom Docker image with RCC runner (action server invokes containerized workflows)

## Next Steps
- Determine optimal input method for work items
- Implement File Adapter POC with action server orchestration
- Design database schema for work item management
- Implement action server monitoring and reporting layer


here are some previous implementations at controlling robcorp rcc with action server for you to examine for reference:

import os
import black
import subprocess
from typing import List
from sema4ai.actions import Response, action





@action
def run_shell_command(cmd: List[str], cwd: str = None) -> Response[str]:
    """
    MIGHTY GORILLA HELPER TO RUN RCC COMMANDS WITH POWER!
    
    Args:
        cmd: List of command parts to run (e.g., ["ls", "-la"] not ["ls -la"])
        cwd: Directory to run the command in (optional)
    
    Returns:
        Response with combined stdout and stderr from command
    
    Raises:
        subprocess.CalledProcessError: If command fails
    """
    # Validate input parameters
    if not cmd:
        return Response(error="Command list cannot be empty")
    
    # Filter out empty strings from command list
    cmd = [part for part in cmd if part.strip()]
    
    if not cmd:
        return Response(error="Command list contains only empty strings")
    
    # Check if user accidentally passed a single string with spaces
    if len(cmd) == 1 and ' ' in cmd[0]:
        return Response(error=f"Command appears to contain spaces: '{cmd[0]}'. Please split into separate list items. For example: ['ls', '-la'] instead of ['ls -la']")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        # Combine stdout and stderr for better error reporting
        output = result.stdout + result.stderr if result.stderr else result.stdout
        try:
            result.check_returncode()
        except subprocess.CalledProcessError:
            print(f"Command failed with return code {result.returncode}")
            print(f"Command output: {output}")
        return Response(result=output)
    except FileNotFoundError as e:
        return Response(error=f"Command not found: {cmd[0]}. Make sure the command exists and is in your PATH. Error: {str(e)}")
    except Exception as e:
        return Response(error=f"Error executing command: {str(e)}")

# Add a non-decorated version for internal use

def _run(cmd: List[str], cwd: str = None) -> str:
    """Internal helper function that calls run_shell_command and extracts the result"""
    response = run_shell_command(cmd, cwd=cwd)
    if hasattr(response, 'error') and response.error:
        raise Exception(response.error)
    return response.result if hasattr(response, 'result') else str(response)


# SCAFFOLDING & TEMPLATES ACTIONS 🦍
@action
def create_robot(template: str, directory: str) -> Response[str]:
    """
    CREATE NEW ROBOT WITH MIGHTY TEMPLATE!
    
    Args:
        template: Template to use (like "01-python")
        directory: Where to create robot
        
    Returns:
        Response with command output
    """
    # Create the directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)
    
    # Initialize the robot using RCC
    output = _run(["rcc", "robot", "initialize", "--template", template, "--directory", directory])
    
    #need to check what the output is
    #check output results
    print(output)
    if "OK" in output:
        # SMASH MORE UPDATES INTO ROBOT CREATION!
        # Update robot configuration files with default content
        update_robot_yaml(directory, robot_yaml_content="")
        update_conda_yaml(directory, conda_yaml_content="")
        update_robot_task_code(directory, task_code="")
        
        return Response(result=f"Robot created from template {template} in {directory} with all config files updated!")
    else:
        return Response(error=f"Failed to create robot from template {template} here is the error: {output}")

@action 
def pull_robot(owner_repo: str, directory: str) -> Response[str]:
    """
    PULL ROBOT FROM REMOTE JUNGLE!
    
    Args:
        owner_repo: Git repo owner and repo name (like "user/repo")
        directory: Where to put robot
        
    Returns:
        Command output with success/failure status
    """
    try:
        output = _run(["rcc", "pull", f"github.com/{owner_repo}", "--directory", directory])
        print(f"Command output: {output}")
        
        # Check for specific success patterns in the output
        success_indicators = [
            "OK.",
            "Flattening path",
            "extracted files"
        ]
        
        if any(indicator in output for indicator in success_indicators):
            return Response(result=f"Robot successfully pulled from {owner_repo} into {directory}. Details: {output}")
        else:
            return Response(error=f"Failed to pull robot from {owner_repo}. Output: {output}")
    except Exception as e:
        return Response(error=f"Error pulling robot: {str(e)}")

# LISTING & RUNNING ACTIONS 🍌
@action
def list_templates() -> Response[str]:
    """
    SHOW ALL ROBOT TEMPLATES!
    
    Returns:
        Response with list of available templates
    """
    result = _run(["rcc", "robot", "initialize", "--list"])
    return Response(result=result)

@action
def pull_template(repo_url: str, directory: str) -> Response[str]:
    """
    GRAB TEMPLATE FROM GITHUB JUNGLE!
    
    Args:
        repo_url: Github repo URL with template
        directory: Where to put template
        
    Returns:
        Command output
    """
    result = _run(["rcc", "pull", repo_url, "-d", directory])
    return Response(result=result)

@action
def create_from_template(template: str, directory: str) -> Response[str]:
    """
    MAKE NEW ROBOT FROM TEMPLATE!
    
    Args:
        template: Template name like python-minimal
        directory: Where to create robot
        
    Returns:
        Response with command output
    """
    result = _run(["rcc", "create", template, "-d", directory])
    return Response(result=result)

@action
def run_robot(task_name: str, robot_path: str) -> Response[str]:
    """
    RUN ONE TASK BY NAME!
    
    Args:
        task_name: Name of task to run
        robot_path: Path to robot directory
        
    Returns:
        Command output
    """
    result = _run(["rcc", "run", "-r", f"{robot_path}/robot.yaml"])
    return Response(result=result)

@action
def task_testrun() -> str:
    """
    DO CLEAN TEST RUN!
    
    Returns:
        Test results output
    """
    return _run(["rcc", "task", "testrun"])

# ROBOT-SCOPED ACTIONS 🍌
@action
def initialize_robot(robot_name: str, template: str) -> Response[str]:
    """
    MAKE NEW ROBOT WITH NAME AND TEMPLATE!
    
    Args:
        robot_name: Name for new robot
        template: Template to use for robot
        
    Returns:
        Response with command output
    """
    result = _run(["rcc", "robot", "init", "--name", robot_name, "--template", template])
    return Response(result=result)

@action
def robot_dependencies() -> Response[str]:
    """
    CHECK ROBOT NEEDS BANANAS!
    
    Returns:
        Response with dependencies check output
    """
    result = _run(["rcc", "robot", "dependencies"])
    return Response(result=result)

@action 
def robot_diagnostics() -> Response[str]:
    """
    CHECK IF ROBOT HEALTHY!
    
    Returns:
        Response with diagnostics output
    """
    result = _run(["rcc", "robot", "diagnostics"])
    return Response(result=result)

@action
def wrap_robot() -> Response[str]:
    """
    PACK ROBOT IN BANANA LEAF!
    
    Returns:
        Response with wrap output
    """
    result = _run(["rcc", "robot", "wrap"])
    return Response(result=result)

@action
def unwrap_robot(artifact: str) -> Response[str]:
    """
    UNWRAP ROBOT FROM BANANA LEAF!
    
    Args:
        artifact: Path to wrapped robot artifact
        
    Returns:
        Command output
    """
    result = _run(["rcc", "robot", "unwrap", "--artifact", artifact])
    return Response(result=result)

# LOCAL EXECUTION ACTIONS 🦍


@action
def run_task(task_name: str) -> Response[str]:
    """
    MAKE ROBOT DO SPECIFIC TASK!
    
    Args:
        task_name: Name of task to run
        
    Returns:
        Response with task output 
    """
    result = _run(["rcc", "run", "--task", task_name])
    return Response(result=result)

@action
def list_tasks() -> Response[str]:
    """
    SHOW ALL TASKS ROBOT CAN DO!
    
    Returns:
        Response with tasks list
    """
    result = _run(["rcc", "task", "list"])
    return Response(result=result)




@action
def script_in_robot(command: str) -> str:
    """
    RUN COMMAND IN ROBOT HOME!
    
    Args:
        command: Shell command to run
        
    Returns:
        Command output
    """
    return _run(["rcc", "run", "--", command])



# DOCS & HELP ACTIONS 🦍
@action
def docs_list() -> Response[str]:
    """
    SHOW ALL DOCUMENTATION!
    
    Returns:
        Response with docs list
    """
    result = _run(["rcc", "docs", "list"])
    return Response(result=result)

@action
def docs_recipes() -> Response[str]:
    """
    SHOW ROBOT RECIPES!
    
    Returns:
        Response with recipes list
    """
    result = _run(["rcc", "docs", "recipes"])
    return Response(result=result)

@action
def docs_changelog() -> Response[str]:
    """
    SHOW WHAT CHANGED!
    
    Returns:
        Response with changelog
    """
    result = _run(["rcc", "docs", "changelog"])
    return Response(result=result)




@action
def help() -> Response[str]:
    """
    SHOW RCC HELP MESSAGE!

    Returns:
        Response with the RCC CLI help output.
    """
    result = _run(["rcc", "--help"])
    return Response(result=result)

@action
def prebuild_holotree() -> Response[str]:
    """
    PREBUILD RCC ENVIRONMENT FOR FASTER ROBOT RUNS!

    This prebuilds the rcc environment for the robot,
    making it quicker and faster to run subsequent tasks.
    
    Returns:
        Response with holotree vars output
    """
    result = _run(["rcc", "holotree", "vars"])
    return Response(result=result)

@action
def update_robot_task_code(robot_name: str, task_code: str) -> Response[str]:
    """
    Replaces tasks.py content in the specified robot with the provided input.

    Args:
        robot_name: The directory/name of the robot to update
        task_code: The source code to place into the tasks.py

    Returns:
        A success message.
    """
    try:
        # Format the code using black if code is provided
        if task_code.strip():
            formatted_code = black.format_str(task_code, mode=black.FileMode())
        else:
            formatted_code = task_code

        # Construct the path to tasks.py in the robot directory
        tasks_py_path = os.path.join(robot_name, "tasks.py")

        # Write the formatted code to tasks.py
        with open(tasks_py_path, "w") as tasks_py:
            tasks_py.write(formatted_code)

        return Response(result=f"Successfully updated the tasks at {tasks_py_path}")
    except Exception as e:
        return Response(error=f"Failed to update tasks.py: {str(e)}")

@action
def update_robot_yaml(robot_directory: str, robot_yaml_content: str) -> Response[str]:
    """
    Update the robot.yaml file in the specified robot directory.

    Args:
        robot_directory: The directory containing the robot
        robot_yaml_content: The YAML content to write into the robot.yaml file

    Returns:
        A success message.
    """
    try:
        robot_yaml_path = os.path.join(robot_directory, "robot.yaml")
        
        with open(robot_yaml_path, "w") as robot_yaml:
            robot_yaml.write(robot_yaml_content)

        return Response(result=f"Successfully updated the robot.yaml at {robot_yaml_path}")
    except Exception as e:
        return Response(error=f"Failed to update robot.yaml: {str(e)}")

@action
def update_conda_yaml(robot_directory: str, conda_yaml_content: str) -> Response[str]:
    """
    Update the conda.yaml file in the specified robot directory.

    Args:
        robot_directory: The directory containing the robot
        conda_yaml_content: The YAML content to write into the conda.yaml file

    Returns:
        A success message.
    """
    try:
        conda_yaml_path = os.path.join(robot_directory, "conda.yaml")
        
        with open(conda_yaml_path, "w") as conda_yaml:
            conda_yaml.write(conda_yaml_content)

        return Response(result=f"Successfully updated the conda.yaml at {conda_yaml_path}")
    except Exception as e:
        return Response(error=f"Failed to update conda.yaml: {str(e)}")
