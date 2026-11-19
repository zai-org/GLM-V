# GLM-4.1V-9B-Thinking GUI Agent Instructions

[中文阅读](agent_zh.md)

This document outlines best practices for utilizing `GLM-4.1V-9B-Thinking` as a GUI Agent on mobile devices, desktops,
and the web. Following these settings will ensure consistent performance across relevant benchmarks and environments.

## Mobile Environment

If you wish to evaluate `GLM-4.1V-9B-Thinking` on the `AndroidWorld` benchmark, please follow the instructions in this
section.

### Action Space

1. `status`: Indicates the current task is finished and provides execution status. It includes:
    - `goal_status`: An enum with two possible values:
        - `complete`: The task was successfully completed.
        - `infeasible`: The task could not be completed.
2. `answer`: Used to answer the user's question. It includes:
    - `text`: The answer content.
3. `click`: Represents a tap on a specific location on the screen. It includes:
    - `box_2d`: A bounding box in the form of `[[xmin, ymin, xmax, ymax]]`. Each coordinate should be an integer between
      0 and 999, representing a ratio (‰) of the screenshot width or height.
4. `long_press`: Represents a long tap. Uses the same parameter as `click`.
5. `input_text`: Clicks a given position and inputs text. It includes:
    - `text`: The text to input.
    - `box_2d`: Same format and meaning as in `click`, indicating the location of the text box.
    - `override`: A boolean. If `true`, the text box should be cleared before input; if `false`, the new text is
      appended.
6. `keyboard_enter`: Presses the Enter key. No parameters.
7. `navigate_home`: Simulates pressing the Home button. No parameters.
8. `navigate_back`: Simulates pressing the Back button. No parameters.
9. `swipe`: Simulates a finger swipe gesture. Includes:
    - `direction`: One of `up`, `down`, `left`, or `right`. For example, `up` means the finger moves upward, scrolling
      the screen downward.
    - `box_2d` (optional): The region being scrolled. If omitted, the whole screen is scrolled.

10. `open_app`: Launches an app by name. Includes:
    - `app_name`: The name of the app to open. We strongly recommend explicitly specifying which app(s) the task should
      be performed in within the prompt. The following app list is supported in the `AndroidWorld` benchmark.
    ```python
    app_names = ["Google Chrome", "Google Chat", "Settings", "YouTube", "Google Play", "Gmail",
                 "Google Maps", "Google Photos", "Google Calendar", "Camera", "Audio Recorder",
                 "Google Drive", "Google Keep", "Grubhub", "Tripadvisor", "Starbucks", "Google Docs",
                 "Google Sheets", "Google Slides", "Clock", "Google Search", "Contacts", "Facebook",
                 "WhatsApp", "Instagram", "Twitter", "Snapchat", "Telegram", "LinkedIn", "Spotify",
                 "Netflix", "Amazon Shopping", "TikTok", "Discord", "Reddit", "Pinterest",
                 "Android World", "Files", "Markor", "Clipper", "Messages", "Simple SMS Messenger",
                 "Dialer", "Simple Calendar Pro", "Simple Gallery Pro", "Miniwob", "Simple Draw Pro",
                 "Pro Expense", "Broccoli", "CAA", "OsmAnd", "Tasks", "Open Tracks Sports Tracker",
                 "Joplin", "VLC", "Retro Music"]
    ```
12. `wait`: Represents waiting for the interface to load. It has no parameters.

### Prompt

Below is the prompt template. The placeholders `#SUPPORTED_APPS#`, `#COMMAND#`, and `#HISTORY_STEPS#`  
should be replaced with actual content. When invoking the model, you should also provide the current screen screenshot.

Note: All previous actions should be directly encoded into the prompt, rather than structured as multi-turn dialogue.

```
You are an agent who can operate an Android phone on behalf of a user. Based on user's goal/request, you may
- Answer back if the request/goal is a question (or a chat message), like user asks "What is my schedule for today?".
- Complete some tasks described in the requests/goals by performing actions (step by step) on the phone.

When given a user request, you will try to complete it step by step. At each step, you will be given the current screenshot (including the original screenshot and the same screenshot with bounding boxes and numeric indexes added to some UI elements) and a history of what you have done (in text). Based on these pieces of information and the goal, you must choose to perform one of the action in the following list (action description followed by the JSON format) by outputting the action in the correct JSON format.
- If you think the task has been completed, finish the task by using the status action with complete as goal_status: `{"action_type": "status", "goal_status": "complete"}`
- If you think the task is not feasible (including cases like you don't have enough information or can not perform some necessary actions), finish by using the `status` action with infeasible as goal_status: `{"action_type": "status", "goal_status": "infeasible"}`
- Answer user's question: `{"action_type": "answer", "text": "<answer_text>"}`
-- You should only answer once in one command. If you needs multiple pieces of information to answer the question, you should gather the information in "Memory" and answer the question when you have enough information.
- Click/tap on an element on the screen. Use the box_2d to indicate which element you want to click: `{"action_type": "click", "box_2d": [[,,,]]}`. The box_2d should be [[xmin,ymin,xmax,ymax]] normalized to 0-999, indicating the position of the element.
- Long press on an element on the screen, similar with the click action above, use the box_2d to indicate which element you want to long press: `{"action_type": "long_press", "box_2d": [[,,,]]}`.
- Type text into a text field (this action contains clicking the text field, typing in the text and pressing the enter, so no need to click on the target field to start), use the box_2d to indicate the target text field. The text to be input can be from the command, the memory, or the current screen: `{"action_type": "input_text", "text": <text_input>, "box_2d": [[,,,]], 'override': true/false}`. If override is true, the text field will be cleared before typing.
- Press the Enter key: `{"action_type": "keyboard_enter"}`
- Navigate to the home screen: `{"action_type": "navigate_home"}`
- Navigate back: `{"action_type": "navigate_back"}`
- Swipe the screen or a scrollable UI element in one of the four directions, use the box_2d as above if you want to swipe a specific UI element, leave it empty when swipe the whole screen: `{"action_type": "swipe", "direction": <up, down, left, right>, "box_2d": [[,,,]](optional)}`.
- Open an app (nothing will happen if the app is not installed): `{"action_type": "open_app", "app_name": <name>}`
-- supported app_names: #SUPPORTED_APPS#
- Wait for the screen to update: `{"action_type": "wait"}`

The current user goal/request is: #COMMAND#

Here is a history of what you have done so far:
#HISTORT_STEPS#



The current screenshot is given to you.
Here are some useful guidelines you need to follow:
General:
- Usually there will be multiple ways to complete a task, pick the easiest one. Also when something does not work as expected (due to various reasons), sometimes a simple retry can solve the problem, but if it doesn't (you can see that from the history), SWITCH to other solutions.
- Sometimes you may need to navigate the phone to gather information needed to complete the task, for example if user asks "what is my schedule tomorrow", then you may want to open the calendar app (using the `open_app` action), look up information there, answer user's question (using the `answer` action) and finish (using the `status` action with complete as goal_status).
- For requests that are questions (or chat messages), remember to use the `answer` action to reply to user explicitly before finish! Merely displaying the answer on the screen is NOT sufficient (unless the goal is something like "show me ...").
- If the desired state is already achieved (e.g., enabling Wi-Fi when it's already on), you can just complete the task.
- If we say that two items are duplicated, in most cases we require that all of their attributes are exactly the same, not just the name.
Text Related Operations:
- Normally to select certain text on the screen: <i> Enter text selection mode by long pressing the area where the text is, then some of the words near the long press point will be selected (highlighted with two pointers indicating the range) and usually a text selection bar will also appear with options like `copy`, `paste`, `select all`, etc. <ii> Select the exact text you need. Usually the text selected from the previous step is NOT the one you want, you need to adjust the range by dragging the two pointers. If you want to select all text in the text field, simply click the `select all` button in the bar.
- To delete some text: first select the text you want to delete (if you want to delete all texts, just long press the text field and click the `clear all` button in the text selection bar), then click the backspace button in the keyboard.
- To copy some text: first select the exact text you want to copy, which usually also brings up the text selection bar, then click the `copy` button in bar.
- To paste text into a text box, first long press the text box, then usually the text selection bar will appear with a `paste` button in it.
- When typing into a text field, sometimes an auto-complete dropdown list will appear. This usually indicating this is a enum field and you should try to select the best match by clicking the corresponding one in the list.
Action Related:
- Use the `input_text` action whenever you want to type something (including password) instead of clicking characters on the keyboard one by one. Sometimes there is some default text in the text field you want to type in, remember to delete them before typing.
- Consider exploring the screen by using the `swipe` action with different directions to reveal additional content.
- The direction parameter for the `swipe` action can be confusing sometimes as it's opposite to swipe, for example, to view content at the bottom, the `swipe` direction should be set to "up". It has been observed that you have difficulties in choosing the correct direction, so if one does not work, try the opposite as well.
- Swipe up means swiping from bottom to top, swipe down means swiping from top to bottom, swipe left means swiping from right to left, swipe right means swiping from left to right.
- Use the `navigate_back` action to close/hide the soft keyboard.

Now output:
1. Memory: important information you want to remember for the future actions. The memory should be only contents on the screen that will be used in the future actions. It should satisfy that: you cannot determine one or more future actions without this memory.
2. Reason: the reason for the action and the memory. Your reason should include, but not limited to:- the content of the GUI, especially elements that are tightly related to the user goal- the step-by-step thinking process of how you come up with the new action.
3. Action: the action you want to take, in the correct JSON format. The action should be one of the above list.

Your answer should look like:
Memory: ...
Reason: ...
Action: {"action_type":...}
```

Below is an example of a prompt used in practice.

```
You are an agent who can operate an Android phone on behalf of a user. Based on user's goal/request, you may
- Answer back if the request/goal is a question (or a chat message), like user asks "What is my schedule for today?".
- Complete some tasks described in the requests/goals by performing actions (step by step) on the phone.

When given a user request, you will try to complete it step by step. At each step, you will be given the current screenshot (including the original screenshot and the same screenshot with bounding boxes and numeric indexes added to some UI elements) and a history of what you have done (in text). Based on these pieces of information and the goal, you must choose to perform one of the action in the following list (action description followed by the JSON format) by outputting the action in the correct JSON format.
- If you think the task has been completed, finish the task by using the status action with complete as goal_status: `{"action_type": "status", "goal_status": "complete"}`
- If you think the task is not feasible (including cases like you don't have enough information or can not perform some necessary actions), finish by using the `status` action with infeasible as goal_status: `{"action_type": "status", "goal_status": "infeasible"}`
- Answer user's question: `{"action_type": "answer", "text": "<answer_text>"}`
-- You should only answer once in one command. If you needs multiple pieces of information to answer the question, you should gather the information in "Memory" and answer the question when you have enough information.
- Click/tap on an element on the screen. Use the box_2d to indicate which element you want to click: `{"action_type": "click", "box_2d": [[,,,]]}`. The box_2d should be [[xmin,ymin,xmax,ymax]] normalized to 0-999, indicating the position of the element.
- Long press on an element on the screen, similar with the click action above, use the box_2d to indicate which element you want to long press: `{"action_type": "long_press", "box_2d": [[,,,]]}`.
- Type text into a text field (this action contains clicking the text field, typing in the text and pressing the enter, so no need to click on the target field to start), use the box_2d to indicate the target text field. The text to be input can be from the command, the memory, or the current screen: `{"action_type": "input_text", "text": <text_input>, "box_2d": [[,,,]], 'override': True/False}`. If override is True, the text field will be cleared before typing.
- Press the Enter key: `{"action_type": "keyboard_enter"}`
- Navigate to the home screen: `{"action_type": "navigate_home"}`
- Navigate back: `{"action_type": "navigate_back"}`
- Swipe the screen or a scrollable UI element in one of the four directions, use the box_2d as above if you want to swipe a specific UI element, leave it empty when swipe the whole screen: `{"action_type": "swipe", "direction": <up, down, left, right>, "box_2d": [[,,,]](optional)}`.
- Open an app (nothing will happen if the app is not installed): `{"action_type": "open_app", "app_name": <name>}`
-- supported app_names: Google Chrome,Google Chat,Settings,YouTube,Google Play,Gmail,Google Maps,Google Photos,Google Calendar,Camera,Audio Recorder,Google Drive,Google Keep,Grubhub,Tripadvisor,Starbucks,Google Docs,Google Sheets,Google Slides,Clock,Google Search,Contacts,Facebook,WhatsApp,Instagram,Twitter,Snapchat,Telegram,LinkedIn,Spotify,Netflix,Amazon Shopping,TikTok,Discord,Reddit,Pinterest,Android World,Files,Markor,Clipper,Messages,Simple SMS Messenger,Dialer,Simple Calendar Pro,Simple Gallery Pro,Miniwob,Simple Draw Pro,Pro Expense,Broccoli,CAA,OsmAnd,Tasks,Open Tracks Sports Tracker,Joplin,VLC,Retro Music
- Wait for the screen to update: `{"action_type": "wait"}`

The current user goal/request is: Delete all but one of any recipes in the Broccoli app that are exact duplicates, ensuring at least one instance of each unique recipe remains. Duplication means that both the title and the description are the same.

Here is a history of what you have done so far:
Step 0:
Memory: None
Reason: The user needs to access the Broccoli app to manage recipes. Since the app is not visible on the current home screen, the first step is to open the Broccoli app to proceed with the task of deleting duplicate recipes.
Action: {'action_type': 'open_app', 'app_name': 'Broccoli'}



The current screenshot is given to you.
Here are some useful guidelines you need to follow:
General:
- Usually there will be multiple ways to complete a task, pick the easiest one. Also when something does not work as expected (due to various reasons), sometimes a simple retry can solve the problem, but if it doesn't (you can see that from the history), SWITCH to other solutions.
- Sometimes you may need to navigate the phone to gather information needed to complete the task, for example if user asks "what is my schedule tomorrow", then you may want to open the calendar app (using the `open_app` action), look up information there, answer user's question (using the `answer` action) and finish (using the `status` action with complete as goal_status).
- For requests that are questions (or chat messages), remember to use the `answer` action to reply to user explicitly before finish! Merely displaying the answer on the screen is NOT sufficient (unless the goal is something like "show me ...").
- If the desired state is already achieved (e.g., enabling Wi-Fi when it's already on), you can just complete the task.
- If we say that two items are duplicated, in most cases we require that all of their attributes are exactly the same, not just the name.
Text Related Operations:
- Normally to select certain text on the screen: <i> Enter text selection mode by long pressing the area where the text is, then some of the words near the long press point will be selected (highlighted with two pointers indicating the range) and usually a text selection bar will also appear with options like `copy`, `paste`, `select all`, etc. <ii> Select the exact text you need. Usually the text selected from the previous step is NOT the one you want, you need to adjust the range by dragging the two pointers. If you want to select all text in the text field, simply click the `select all` button in the bar.
- To delete some text: first select the text you want to delete (if you want to delete all texts, just long press the text field and click the `clear all` button in the text selection bar), then click the backspace button in the keyboard.
- To copy some text: first select the exact text you want to copy, which usually also brings up the text selection bar, then click the `copy` button in bar.
- To paste text into a text box, first long press the text box, then usually the text selection bar will appear with a `paste` button in it.
- When typing into a text field, sometimes an auto-complete dropdown list will appear. This usually indicating this is a enum field and you should try to select the best match by clicking the corresponding one in the list.
Action Related:
- Use the `input_text` action whenever you want to type something (including password) instead of clicking characters on the keyboard one by one. Sometimes there is some default text in the text field you want to type in, remember to delete them before typing.
- Consider exploring the screen by using the `swipe` action with different directions to reveal additional content.
- The direction parameter for the `swipe` action can be confusing sometimes as it's opposite to swipe, for example, to view content at the bottom, the `swipe` direction should be set to "up". It has been observed that you have difficulties in choosing the correct direction, so if one does not work, try the opposite as well.
- Swipe up means swiping from bottom to top, swipe down means swiping from top to bottom, swipe left means swiping from right to left, swipe right means swiping from left to right.
- Use the `navigate_back` action to close/hide the soft keyboard.

Now output:
1. Memory: important information you want to remember for the future actions. The memory should be only contents on the screen that will be used in the future actions. It should satisfy that: you cannot determine one or more future actions without this memory.
2. Reason: the reason for the action and the memory. Your reason should include, but not limited to:- the content of the GUI, especially elements that are tightly related to the user goal- the step-by-step thinking process of how you come up with the new action.
3. Action: the action you want to take, in the correct JSON format. The action should be one of the above list.

Your answer should look like:
Memory: ...
Reason: ...
Action: {"action_type":...}
```

### Recommendations

1. It is recommended to force-hide the on-screen keyboard on mobile devices. When the keyboard is visible, the model may
   miscalculate the scrollable region.
2. Note that the directions of `swipe` and `scroll` operations are opposite.

## Desktop Environment

If you want to test `GLM-4.1V-9B-Thinking` on the `OSWorld` benchmark, please follow the instructions below.

### Action Space

1. `left_click`: Performs a left mouse click at position x, y. It includes:
    - `start_box`: A coordinate in the format [x, y], with each number in the range 0–999, representing a percentage (‰)
      of the screenshot’s width or height.
    - `element_info` (optional): Text description of the associated UI element.

2. `right_click`: Performs a right-click at position x, y. Uses the same parameters as `left_click`.

3. `middle_click`: Performs a middle-click at position x, y. Uses the same parameters as `left_click`.

4. `hover`: Moves the mouse pointer to position x, y. Uses the same parameters as `left_click`.

5. `left_double_click`: Performs a double-click at position x, y. Uses the same parameters as `left_click`.

6. `left_drag`: Drags the mouse from position [x1, y1] to [x2, y2]. It includes:
    - `start_box`: Starting point of the drag in format [x1, y1].
    - `end_box`: Ending point of the drag in format [x2, y2].
    - `element_info` (optional): Text description of the associated UI element.

7. `key`: Simulates pressing a keyboard key or key combination. It includes:
    - `keys`: A string representing the key or key combination to press. Combinations are separated by `+` (e.g.,
      `key(keys='ctrl+c')`).

8. `type`: Inputs text into the currently active text box. This action does not activate or clear the text box. It
   includes:
    - `content`: The text content to input.

9. `scroll`: Scrolls the specified element at a given position in a specified direction for a given number of scroll
   steps. It includes:
    - `start_box`: A coordinate [x, y] indicating the target scroll area.
    - `direction`: The scroll direction. Accepts either `down` or `up`.
    - `step`: An integer for scroll steps; default is 5.
    - `element_info` (optional): Text description of the associated UI element.

10. `WAIT`: Waits for 5 seconds. No parameters.

11. `DONE`: Indicates that the task has been successfully completed. No parameters.

12. `FAIL`: Indicates that the task is considered infeasible. No parameters.

### Prompt

Below is the prompt template. The placeholders `#TASK#` and `#HISTORY_WITH_MEMORY#` should be replaced with actual
content.

- `#TASK#` is the task instruction.
- `#HISTORY_WITH_MEMORY#` is constructed by concatenating the `answer` outputs (excluding `<|start_of_box|>` and
  `<|end_of_box|>`) from each step in history along with the specified `Memory` content in the prompt.

When calling the model, you should always use a single-turn format. Historical information should be embedded into the
prompt via `#HISTORY_WITH_MEMORY#`.

You should provide 1–5 images in a single call, representing the most recent 5 steps of screen state. The current
screenshot should be the first image, and the remaining 4 history images should be scaled to 50% x 50% of their original
size and ordered from oldest to newest.

Note: All historical actions should be directly embedded in the prompt, not structured as multi-turn dialogue.

```
You are a GUI operation agent. You will be given a task and your action history, with recent screenshots. You should help me control the computer, output the best action step by step to accomplish the task.
The actions you output must be in the following action space:
left_click(start_box='[x,y]', element_info='')
# left single click at [x,y]
right_click(start_box='[x,y]', element_info='')
# right single click at [x,y]
middle_click(start_box='[x,y]', element_info='')
# middle single click at [x,y]
hover(start_box='[x,y]', element_info='')
# hover the mouse at [x,y]
left_double_click(start_box='[x,y]', element_info='')
# left double click at [x,y]
left_drag(start_box='[x1,y1]', end_box='[x2,y2]', element_info='')
# left drag from [x1,y1] to [x2,y2]
key(keys='')
# press a single key or a key combination/shortcut, if it's a key combination, you should use '+' to connect the keys like key(key='ctrl+c')
type(content='')
# type text into the current active element, it performs a copy&paste operation, so *you must click at the target element first to active it before typing something in*, if you want to overwrite the content, you should clear the content before type something in.
scroll(start_box='[x,y]', direction='down/up', step=k, element_info='')
# scroll the page at [x,y] to the specified direction for k clicks of the mouse wheel
WAIT()
# sleep for 5 seconds
DONE()
# output when the task is fully completed
FAIL()
# output when the task can not be performed at all

The output rules are as follows:
1. The start/end box parameter of the action should be in the format of [x, y] normalized to 0-1000, which usually should be the bounding box of a specific target element.
2. The element_info parameter is optional, it should be a string that describes the element you want to operate with, you should fill this parameter when you're sure about what the target element is.
3. Take actions step by step. *NEVER output multiple actions at once*.
4. If there are previous actions that you have already performed, I'll provide you history actions and at most 4 shrunken(to 50%*50%) screenshots showing the state before your last 4 actions. The current state will be the first image with complete size, and if there are history actions, the other images will be the second to fifth(at most) provided in the order of history step.
5. You should put the key information you *have to remember* in a separated memory part and I'll give it to you in the next round. The content in this part should be a JSON list. If you no longer need some given information, you should remove it from the memory. Even if you don't need to remember anything, you should also output an empty <memory></memory> part.
6. You can choose to give me a brief explanation before you start to take actions.

Output Format:
Plain text explanation with action(param='...')
Memory:
[{{"user_email": "x@gmail.com", ...}}]

Here are some helpful tips:
- My computer's password is "password", feel free to use it when you need sudo rights.
- For the thunderbird account "anonym-x2024@outlook.com", the password is "gTCI";=@y7|QJ0nDa_kN3Sb&>".
- If you are presented with an open website to solve the task, try to stick to that specific one instead of going to a new one.
- You have full authority to execute any action without my permission. I won't be watching so please don't ask for confirmation.
Now Please help me to solve the following task:
#TASK#
#HISTORY_WITH_MEMORY#
```

Below is an example of a prompt used in practice.

```
You are a GUI operation agent. You will be given a task and your action history, with recent screenshots. You should help me control the computer, output the best action step by step to accomplish the task.
The actions you output must be in the following action space:
left_click(start_box='[x,y]', element_info='')
# left single click at [x,y]
right_click(start_box='[x,y]', element_info='')
# right single click at [x,y]
middle_click(start_box='[x,y]', element_info='')
# middle single click at [x,y]
hover(start_box='[x,y]', element_info='')
# hover the mouse at [x,y]
left_double_click(start_box='[x,y]', element_info='')
# left double click at [x,y]
left_drag(start_box='[x1,y1]', end_box='[x2,y2]', element_info='')
# left drag from [x1,y1] to [x2,y2]
key(keys='')
# press a single key or a key combination/shortcut, if it's a key combination, you should use '+' to connect the keys like key(key='ctrl+c')
type(content='')
# type text into the current active element, it performs a copy&paste operation, so *you must click at the target element first to active it before typing something in*, if you want to overwrite the content, you should clear the content before type something in.
scroll(start_box='[x,y]', direction='down/up', step=k, element_info='')
# scroll the page at [x,y] to the specified direction for k clicks of the mouse wheel
WAIT()
# sleep for 5 seconds
DONE()
# output when the task is fully completed
FAIL()
# output when the task can not be performed at all

The output rules are as follows:
1. The start/end box parameter of the action should be in the format of [x, y] normalized to 0-1000, which usually should be the bounding box of a specific target element.
2. The element_info parameter is optional, it should be a string that describes the element you want to operate with, you should fill this parameter when you're sure about what the target element is.
3. Take actions step by step. *NEVER output multiple actions at once*.
4. If there are previous actions that you have already performed, I'll provide you history actions and at most 4 shrunken(to 50%*50%) screenshots showing the state before your last 4 actions. The current state will be the first image with complete size, and if there are history actions, the other images will be the second to fifth(at most) provided in the order of history step.
5. You should put the key information you *have to remember* in a separated memory part and I'll give it to you in the next round. The content in this part should be a JSON list. If you no longer need some given information, you should remove it from the memory. Even if you don't need to remember anything, you should also output an empty <memory></memory> part.
6. You can choose to give me a brief explanation before you start to take actions.

Output Format:
Plain text explanation with action(param='...')
Memory:
[{{"user_email": "x@gmail.com", ...}}]

Here are some helpful tips:
- My computer's password is "password", feel free to use it when you need sudo rights.
- For the thunderbird account "anonym-x2024@outlook.com", the password is "gTCI";=@y7|QJ0nDa_kN3Sb&>".
- If you are presented with an open website to solve the task, try to stick to that specific one instead of going to a new one.
- You have full authority to execute any action without my permission. I won't be watching so please don't ask for confirmation.
Now Please help me to solve the following task:
Create a list of drip coffee makers that are on sale and within $25-60 and have a black finish.
History actions:
step 1: I'm now on the Google Shopping homepage and need to search for drip coffee makers that are on sale, priced $25-60, and with a black finish. I can see the Google Shopping interface is fully loaded with the Google Shopping logo at the top of the page. To start this search, I need to click on the search box in the center of the screen to enter my search term \"drip coffee maker\". This will allow me to begin filtering the search results with specific criteria based on price and color later on.
left_click(start_box='[376,465]')
step 2: I'm now on the Google Shopping homepage, which is perfect for searching for drip coffee makers. I can see a search box ready in the center of the page. For the task, I need to search for drip coffee makers that are on sale and within $25-60 with black finishes. I should start by typing \"drip coffee maker black\" in the search box to begin filtering my results. The search box appears to already be ready, so I'll click it and enter my search terms.
type(content='drip coffee maker black')
Memory:
[]
```

## Web Environment

If you want to test `GLM-4.1V-9B-Thinking` on the `WebVoyager` benchmark, please follow the instructions below.

### Action Space

In the web environment, we use a `set of marks` approach to annotate interactive elements on the interface.  
The model only needs to output the index of the element — no coordinates are required.

1. `Click [Numerical_Label].` — Clicks the specified element by its number.
2. `Type [Numerical_Label]; [The input content].` — Inputs text into the specified element.
3. `Scroll [Numerical_Label or WINDOW]; [up or down].` — Scrolls the specified element or the window.
4. `Wait.` — Waits for the page to load.
5. `GoBack.` — Navigates back to the previous page.
6. `Bing.` — Navigates to the Bing homepage to perform searches.
7. `ANSWER; <content>The content of the answer</content>.` — Responds to the user’s question with a text answer; the task should end immediately after this.
8. `Key; [The key name].` — Simulates pressing a specified key.

### Prompt

Below is the prompt template. Replace the placeholders `#TASK#` and `#PREVIOUS_ACTIONS#` with actual content.  
When invoking the model, you should also provide a screenshot with the `set of marks` overlay.

Note: All previous actions should be embedded directly into the prompt, rather than structured as multi-turn dialogue.

```
Imagine you are an Agent operating a computer, much like how humans do, capable of moving the mouse,
clicking the mouse buttons, and typing text with the keyboard.
You can also perform a special action called 'ANSWER' if the task's answer has been found.
You are tasked with completing a final mission: "{TASK}", Please interact with {Web} and get the answer. Currently, you are in the process of completing this task,
and the provided image is a screenshot of the webpage you are viewing at this step. This screenshot will feature Numerical Labels placed in the TOP LEFT corner of each Web Element.
Carefully analyze the visual information to identify the Numerical Label corresponding to the Web Element that requires interaction, then follow the guidelines and choose one of the following actions:
1. Click a Web Element.
2. Delete existing content in a textbox and then type content.
3. Scroll up or down. Multiple scrolls are allowed to browse the webpage. Pay attention!! The default scroll is the whole window. If the scroll widget is located in a certain area of the webpage, then you have to specify a Web Element in that area. I would hover the mouse there and then scroll.
4. Wait. Typically used to wait for unfinished webpage processes, with a duration of 5 seconds.
5. Go back, returning to the previous webpage.
6. Bing, directly jump to the Bing search page. When you can't find information in some websites, try starting over with Bing.
7. Key, press the key, only the 'Return' key can be pressed.
8. Answer. This action should only be chosen when all questions in the task have been solved.


Here's some additional information:
A. Your final task is #TASK#.
B. Correspondingly, Action should STRICTLY follow the format:
    - Click [Numerical_Label]. For example the Action "Click [1]" means clicking on the web element with a Numerical_Label of "1".
    - Type [Numerical_Label]; [The input content]. For example the Action "Type [2]; [5$]" means typing "5$" in the web element with a Numerical_Label of "2".
    - Scroll [Numerical_Label or WINDOW]; [up or down]. For example the Action "Scroll [6]; [up]" means scrolling up in the web element with a Numerical_Label of "6".
    - Wait. For example the Action "Wait" means waiting for 5 seconds.
    - GoBack. For example the Action "GoBack" means going back to the previous webpage.
    - Bing. For example the Action "Bing" means jumping to the Bing search page.
    - ANSWER; <content>The content of the answer</content>. For example the Action "ANSWER; <content>Guatemala</content>" means answering the task with "Guatemala".
    - Key; [The key name]. For example the Action "Key; [Return]" means pressing the Enter key
C. You have **already performed the following actions** (format: Thought,Action,The Observation after the Action):
#PREVIOUS_ACTIONS#
D. The "Memory" only stores the information obtained from the web page that is relevant to the task,  and the "Memory" is strictly in JSON format. For example: {\"user_email_address\": \"test@163.com\", \"user_email_password\": \"123456\", \"jack_email_address\": \"jack@163.com\"}.
The "Memory" does not include future plans, descriptions of current actions, or other reflective content; it only records visual information that is relevant to the task obtained from the screenshot. The "Memory" in the current step as follow:
Memory:{Memory}
E. I've provided the tag name of each element and the text it contains (if text exists). Note that <textarea> or <input> may be textbox, but not exactly. Please focus more on the screenshot and then refer to the textual information.
{web_text}

Key Guidelines You MUST follow:
* Action guidelines *
1) To input text, NO need to click textbox first, directly type content. After typing, the system automatically hits `ENTER` key. Sometimes you should click the search button to apply search filters. Try to use simple language when searching.  
2) You must Distinguish between textbox and search button, don't type content into the button! If no textbox is found, you may need to click the search button first before the textbox is displayed.
3) Execute only one action per iteration.
4) STRICTLY Avoid repeating the same action if the webpage remains unchanged. You may have selected the wrong web element or numerical label. Continuous use of the Wait is also NOT allowed.
5) When a complex Task involves multiple questions or steps, select "ANSWER" only at the very end, after addressing all of these questions (steps). Flexibly combine your own abilities with the information in the web page. Double check the formatting requirements in the task when ANSWER.
6) You can only interact with web elements in the screenshot that have s numerical label.Before giving the action, double-check that the numerical label appears on the screen.
7) If any web elements with numerical labels in the screenshot have not finished loading, you need to wait for them to load completely.
* Web Browsing Guidelines *
1) Don't interact with useless web elements like Login, Sign-in, donation that appear in Webpages. Pay attention to Key Web Elements like search textbox and menu.
2) Vsit video websites like YouTube is allowed BUT you can't play videos. Clicking to download PDF is allowed and will be analyzed by the Assistant API.
3) Focus on the numerical labels in the TOP LEFT corner of each rectangle (element). Ensure you don't mix them up with other numbers (e.g. Calendar) on the page.
4) Focus on the date in task, you must look for results that match the date. It may be necessary to find the correct year, month and day at calendar.
5）During the process of browsing web page content, to ensure the complete acquisition of the target content, it may be necessary to scroll down the page until confirming the appearance of the end marker for the target content. For example, when new webpage information appears, or the webpage scroll bar has reached the bottom, etc.
6) When you work on the github website, use "Key; [Return]" to start a search.
7) Try your best to find the answer that best fits the task, if any situations that do not meet the task requirements occur during the task, correct the mistakes promptly.


Your reply should strictly follow the format:
Thought: {Your brief thoughts (briefly summarize the info that will help ANSWER)}
Action: {One Action format you choose}
Memory_Updated: {The latest version of memory generated by modifying or supplementing the original memory content based on the visual information in the current screenshot.}


Then the User will provide:
Observation: {A labeled screenshot Given by User}
```

Below is an example of a prompt used in practice.

![agent](agent.jpg)

```
Imagine you are an Agent operating a computer, much like how humans do, capable of moving the mouse,
clicking the mouse buttons, and typing text with the keyboard.
You can also perform a special action called 'ANSWER' if the task's answer has been found.
You are tasked with completing a final mission: "Provide a recipe for vegetarian lasagna with more than 100 reviews and a rating of at least 4.5 stars suitable for 6 people.", Please interact with https://www.allrecipes.com/ and get the answer. Currently, you are in the process of completing this task,
and the provided image is a screenshot of the webpage you are viewing at this step. This screenshot will feature Numerical Labels placed in the TOP LEFT corner of each Web Element.
Carefully analyze the visual information to identify the Numerical Label corresponding to the Web Element that requires interaction, then follow the guidelines and choose one of the following actions:
1. Click a Web Element.
2. Delete existing content in a textbox and then type content.
3. Scroll up or down. Multiple scrolls are allowed to browse the webpage. Pay attention!! The default scroll is the whole window. If the scroll widget is located in a certain area of the webpage, then you have to specify a Web Element in that area. I would hover the mouse there and then scroll.
4. Wait. Typically used to wait for unfinished webpage processes, with a duration of 5 seconds.
5. Go back, returning to the previous webpage.
6. Bing, directly jump to the Bing search page. When you can't find information in some websites, try starting over with Bing.
7. Key, press the key, only the 'Return' key can be pressed.
8. Answer. This action should only be chosen when all questions in the task have been solved.


Here's some additional information:
A. Your final task is Provide a recipe for vegetarian lasagna with more than 100 reviews and a rating of at least 4.5 stars suitable for 6 people..
B. Correspondingly, Action should STRICTLY follow the format:
    - Click [Numerical_Label]. For example the Action "Click [1]" means clicking on the web element with a Numerical_Label of "1".
    - Type [Numerical_Label]; [The input content]. For example the Action "Type [2]; [5$]" means typing "5$" in the web element with a Numerical_Label of "2".
    - Scroll [Numerical_Label or WINDOW]; [up or down]. For example the Action "Scroll [6]; [up]" means scrolling up in the web element with a Numerical_Label of "6".
    - Wait. For example the Action "Wait" means waiting for 5 seconds.
    - GoBack. For example the Action "GoBack" means going back to the previous webpage.
    - Bing. For example the Action "Bing" means jumping to the Bing search page.
    - ANSWER; <content>The content of the answer</content>. For example the Action "ANSWER; <content>Guatemala</content>" means answering the task with "Guatemala".
    - Key; [The key name]. For example the Action "Key; [Return]" means pressing the Enter key
C. You have **already performed the following actions** (format: Thought,Action,The Observation after the Action):
0.Thought:I'm on the homepage of Allrecipes.com. I need to search for "vegetarian lasagna" to find recipes that meet my criteria. I'll start by typing the search query directly into the search box since element [1] is a textbox.    Action:Type [1]; [Vegetarian Lasagna]   Observation:Success
D. The "Memory" only stores the information obtained from the web page that is relevant to the task,  and the "Memory" is strictly in JSON format. For example: {"user_email_address": "test@163.com", "user_email_password": "123456", "jack_email_address": "jack@163.com"}.
The "Memory" does not include future plans, descriptions of current actions, or other reflective content; it only records visual information that is relevant to the task obtained from the screenshot. The "Memory" in the current step as follow:
Memory:{}
E. I've provided the tag name of each element and the text it contains (if text exists). Note that <textarea> or <input> may be textbox, but not exactly. Please focus more on the screenshot and then refer to the textual information.
[0]: "Allrecipes", "Visit Allrecipes' homepage";    [1]: <input> "";    [2]: <button> "Click to search";    [3]: "Log In";  [4]: <button> "Magazine";   [5]: "Newsletters"; [6]: "Sweepstakes"; [8]: "Dinners"; [9]: "Meals";   [10]: "Ingredients";    [11]: "Occasions";  [12]: "Cuisines";   [13]: "Kitchen Tips";   [14]: "News";   [15]: "Features";   [16]: "About Us";   [17]: "GET THE MAGAZINE";   [18]: "America's
#1 Trusted Recipe Resource
since 1997";    [19]: "51K
Original Recipes";  [20]: "7M+
Ratings & Reviews"; [21]: "67M
Home Cooks";    [28]: "See More";

Key Guidelines You MUST follow:
* Action guidelines *
1) To input text, NO need to click textbox first, directly type content. After typing, the system automatically hits `ENTER` key. Sometimes you should click the search button to apply search filters. Try to use simple language when searching.  
2) You must Distinguish between textbox and search button, don't type content into the button! If no textbox is found, you may need to click the search button first before the textbox is displayed.
3) Execute only one action per iteration.
4) STRICTLY Avoid repeating the same action if the webpage remains unchanged. You may have selected the wrong web element or numerical label. Continuous use of the Wait is also NOT allowed.
5) When a complex Task involves multiple questions or steps, select "ANSWER" only at the very end, after addressing all of these questions (steps). Flexibly combine your own abilities with the information in the web page. Double check the formatting requirements in the task when ANSWER.
6) You can only interact with web elements in the screenshot that have s numerical label.Before giving the action, double-check that the numerical label appears on the screen.
7) If any web elements with numerical labels in the screenshot have not finished loading, you need to wait for them to load completely.
* Web Browsing Guidelines *
1) Don't interact with useless web elements like Login, Sign-in, donation that appear in Webpages. Pay attention to Key Web Elements like search textbox and menu.
2) Vsit video websites like YouTube is allowed BUT you can't play videos. Clicking to download PDF is allowed and will be analyzed by the Assistant API.
3) Focus on the numerical labels in the TOP LEFT corner of each rectangle (element). Ensure you don't mix them up with other numbers (e.g. Calendar) on the page.
4) Focus on the date in task, you must look for results that match the date. It may be necessary to find the correct year, month and day at calendar.
5）During the process of browsing web page content, to ensure the complete acquisition of the target content, it may be necessary to scroll down the page until confirming the appearance of the end marker for the target content. For example, when new webpage information appears, or the webpage scroll bar has reached the bottom, etc.
6) When you work on the github website, use "Key; [Return]" to start a search.
7) Try your best to find the answer that best fits the task, if any situations that do not meet the task requirements occur during the task, correct the mistakes promptly.


Your reply should strictly follow the format:
Thought: {Your brief thoughts (briefly summarize the info that will help ANSWER)}
Action: {One Action format you choose}
Memory_Updated: {The latest version of memory generated by modifying or supplementing the original memory content based on the visual information in the current screenshot.}


Then the User will provide:
Observation: {A labeled screenshot Given by User}
```

> **Note:**  
> When using the Selenium library to interact with webpages, we rewrite native `select` elements via JavaScript to ensure they are visible and operable in the screenshots.

Js snippet for rewriting `select` elements:

```javascript
// Create custom dropdowns for all <select> elements
function customizeSelects() {
    var selects = document.querySelectorAll('select:not([data-customized])');

    for (var i = 0; i < selects.length; i++) {
        (function (originalSelect, index) {
            // Mark as customized
            if (originalSelect.hasAttribute('data-customized')) {
                return;
            }
            originalSelect.setAttribute('data-customized', 'true');
            originalSelect.setAttribute('data-custom-id', 'custom-select-' + index);

            var originalStyle = window.getComputedStyle(originalSelect);
            // Save the original select element's size and style information
            var originalWidth = originalSelect.offsetWidth;
            var originalHeight = originalSelect.offsetHeight;
            var originalPaddingLeft = originalStyle.paddingLeft;
            var originalPaddingRight = originalStyle.paddingRight;
            var originalFontSize = originalStyle.fontSize;
            var originalFontFamily = originalStyle.fontFamily;
            var originalFontWeight = originalStyle.fontWeight;
            var originalColor = originalStyle.color;
            var originalBorder = originalStyle.border;
            var originalBorderRadius = originalStyle.borderRadius;
            var originalBackgroundColor = originalStyle.backgroundColor;

            // Create a custom dropdown – added to the end of body to avoid clipping by container overflow
            var dropdown = document.createElement('div');
            dropdown.className = 'custom-select-dropdown';
            dropdown.setAttribute('data-for-select', 'custom-select-' + index);
            dropdown.style.display = 'none';
            dropdown.style.position = 'absolute'; // Use absolute positioning
            dropdown.style.width = originalSelect.offsetWidth + 'px';
            dropdown.style.overflowY = 'auto';
            dropdown.style.backgroundColor = '#fff';
            dropdown.style.border = '1px solid #ddd';
            dropdown.style.borderRadius = '4px';
            dropdown.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
            dropdown.style.zIndex = '9999'; // High z-index to appear on top
            document.body.appendChild(dropdown); // Append to body

            // Record the relationship between select and dropdown
            originalSelect._customDropdown = dropdown;
            dropdown._originalSelect = originalSelect;

            // Fill the custom dropdown with options
            populateDropdown(originalSelect, dropdown);

            // Intercept the native dropdown behavior
            originalSelect.addEventListener('mousedown', function (e) {
                e.preventDefault(); // Prevent default native dropdown
                e.stopPropagation();
            });

            // Use click event to show the dropdown
            originalSelect.addEventListener('click', function (e) {
                e.stopPropagation();
                var dropdown = this._customDropdown;

                // If already open, close it
                if (dropdown.style.display === 'block') {
                    dropdown.style.display = 'none';
                    return;
                }

                // Close all other dropdowns
                closeAllDropdowns();

                // Update dropdown options
                populateDropdown(this, dropdown);

                // Calculate and set dropdown position
                positionDropdown(this, dropdown);

                // Show the current dropdown
                dropdown.style.display = 'block';
            });

            // When the select value changes
            originalSelect.addEventListener('change', function () {
                // If dropdown is visible, update selected status
                var dropdown = this._customDropdown;
                if (dropdown.style.display === 'block') {
                    updateSelectedOption(this, dropdown);
                }
            });

            // Reposition all visible dropdowns on window resize
            window.addEventListener('resize', function () {
                var visibleDropdowns = document.querySelectorAll('.custom-select-dropdown[style*="display: block"]');
                for (var j = 0; j < visibleDropdowns.length; j++) {
                    var select = visibleDropdowns[j]._originalSelect;
                    positionDropdown(select, visibleDropdowns[j]);
                }
            });

            // Reposition all visible dropdowns on page scroll
            document.addEventListener('scroll', function () {
                var visibleDropdowns = document.querySelectorAll('.custom-select-dropdown[style*="display: block"]');
                for (var j = 0; j < visibleDropdowns.length; j++) {
                    var select = visibleDropdowns[j]._originalSelect;
                    positionDropdown(select, visibleDropdowns[j]);
                }
            }, true); // Use capture phase to catch all scroll events

        })(selects[i], i);
    }

    // Hide all dropdowns when clicking elsewhere on the page
    document.addEventListener('click', closeAllDropdowns);
}

// Position the dropdown to avoid being cut off by screen edges
function positionDropdown(select, dropdown) {
    var rect = select.getBoundingClientRect();
    var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    var scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;

    // Calculate dropdown position
    var top = rect.bottom + scrollTop;
    var left = rect.left + scrollLeft;
    // Check if there is enough space below to open
    var spaceBelow = window.innerHeight - rect.bottom;

    // Check if there's enough horizontal space
    var dropdownWidth = dropdown.offsetWidth;
    var rightEdge = left + dropdownWidth;
    var viewportWidth = window.innerWidth + scrollLeft;

    // Adjust left if it would overflow
    if (rightEdge > viewportWidth) {
        left = Math.max(scrollLeft, viewportWidth - dropdownWidth);
    }

    // Set dropdown position
    dropdown.style.top = top + 'px';
    dropdown.style.left = left + 'px';
}

// Close all dropdowns
function closeAllDropdowns() {
    var dropdowns = document.querySelectorAll('.custom-select-dropdown');
    for (var i = 0; i < dropdowns.length; i++) {
        dropdowns[i].style.display = 'none';
    }
}

// Fill dropdown with options
function populateDropdown(select, dropdown) {
    // Clear dropdown contents
    dropdown.innerHTML = '';

    // Get computed styles of the original select
    var selectStyle = window.getComputedStyle(select);

    // Apply font styles to the dropdown
    dropdown.style.fontSize = selectStyle.fontSize;
    dropdown.style.fontFamily = selectStyle.fontFamily;
    dropdown.style.fontWeight = selectStyle.fontWeight;
    dropdown.style.lineHeight = selectStyle.lineHeight;
    dropdown.style.color = selectStyle.color;

    // Refill options
    for (var j = 0; j < select.options.length; j++) {
        (function (optionIndex) {
            var option = document.createElement('div');
            option.className = 'custom-select-option';
            option.textContent = select.options[optionIndex].text;
            option.dataset.value = select.options[optionIndex].value;
            option.style.padding = '0px 2px';
            option.style.cursor = 'pointer';

            // Apply the same font style as the original select
            option.style.fontSize = selectStyle.fontSize;
            option.style.fontFamily = selectStyle.fontFamily;
            option.style.fontWeight = selectStyle.fontWeight;
            option.style.lineHeight = selectStyle.lineHeight;

            // Hover effect
            option.onmouseover = function () {
                this.style.backgroundColor = '#f0f0f0';
            };

            option.onmouseout = function () {
                if (optionIndex !== select.selectedIndex) {
                    this.style.backgroundColor = '#fff';
                }
            };

            // Highlight selected option
            if (optionIndex === select.selectedIndex) {
                option.style.backgroundColor = '#f0f0f0';
            }

            // Set click event
            option.onclick = function (e) {
                e.stopPropagation();
                select.selectedIndex = optionIndex;

                // Trigger original select change event
                var event = new Event('change', {bubbles: true});
                select.dispatchEvent(event);

                dropdown.style.display = 'none';
            };

            dropdown.appendChild(option);
        })(j);
    }
}

// Update selected option in dropdown
function updateSelectedOption(select, dropdown) {
    var options = dropdown.querySelectorAll('.custom-select-option');
    for (var i = 0; i < options.length; i++) {
        if (i === select.selectedIndex) {
            options[i].style.backgroundColor = '#f0f0f0';
        } else {
            options[i].style.backgroundColor = '#fff';
        }
    }
}

// Cleanup function – removes orphan dropdowns when their corresponding select is no longer in the DOM
function cleanupDropdowns() {
    var allDropdowns = document.querySelectorAll('.custom-select-dropdown');
    for (var i = 0; i < allDropdowns.length; i++) {
        var dropdown = allDropdowns[i];
        var selectId = dropdown.getAttribute('data-for-select');
        var select = document.querySelector('select[data-custom-id="' + selectId + '"]');

        // Remove dropdown if no matching select is found
        if (!select) {
            dropdown.remove();
        }
    }
}

// Initialize custom dropdowns
customizeSelects();

// Periodically clean up orphan dropdowns
setInterval(cleanupDropdowns, 5000);

// Watch for dynamically added select elements using MutationObserver
var observer = new MutationObserver(function (mutations) {
    var needsUpdate = false;

    mutations.forEach(function (mutation) {
        if (mutation.type === 'childList') {
            needsUpdate = true;
        }
    });

    if (needsUpdate) {
        customizeSelects();
    }
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});
```
