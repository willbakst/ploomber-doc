import os
from datetime import date, timedelta


import panel as pn
import pandas as pd
from chat import analyze_image_with_text


from imagekitio import ImageKit
import nest_asyncio

from stock import store_data_in_duckdb, get_data_from_duckdb, get_stock_symbols
from bokeh.themes import Theme
from bokeh.io import curdoc


pd.options.plotting.backend = "plotly"

img_private = os.getenv("image_private_key")
img_public = os.getenv("image_public_key")
img_endpoint = os.getenv("image_url_endpoint")

curdoc().theme = Theme(json={})


# needed because  Panel starts up the ioloop
nest_asyncio.apply()

# Initialize Panel with extensions for plotting
pn.extension("plotly")


def save_image():
    """

    Content of upload object

    {
    'fileId': '6311960051c0c0bdd51cff53',
    'name': 'test-url_9lQZRkh8J.jpg',
    'size': 1222,
    'versionInfo': {
        'id': '6311960051c0c0bdd51cff53',
        'name': 'Version 1'
    },
    'filePath': '/test-url_9lQZRkh8J.jpg',
    'url': 'https://ik.imagekit.io/your_imagekit_id/test-url_9lQZRkh8J.jpg',
    'fileType': 'non-image',
    'tags': ['tag1', 'tag2'],
    'AITags': None,
    'isPrivateFile': False
    }

    """
    imagekit = ImageKit(
        private_key=img_private, public_key=img_public, url_endpoint=img_endpoint
    )

    upload = imagekit.upload_file(
        file=open("plot_image.png", "rb"),
        file_name="test-file.jpg",
    )

    result = upload.response_metadata.raw

    return result["url"]


def save_plot(plot, filename="plot.png"):
    plot.write_image(filename)


def update_visualization(ticker, start, end, data_instruction, question):
    # Fetch the stock data from DuckDB
    print(type(start))
    store_data_in_duckdb(ticker, start, end, db_file="stockdata.duckdb")
    data = get_data_from_duckdb(stat_dic[data_instruction], ticker, start, end)

    try:
        # Generate the plot
        plot = data.plot.line(
            x="Date",
            y=stat_dic[data_instruction],
            color="Ticker",
            facet_col="Ticker",
            title=f"{' '.join(ticker)}: {data_instruction} from {start} to {end}",
        )

        # Display plot
        visualization_area.object = plot
    except Exception as e:
        print(f"Error generating plot: {e}")

    interpretation_area.object = "Generating plot interpretation, please wait..."

    # Save the plot
    save_plot(plot, "plot_image.png")

    result_url = save_image()

    interpretation_text = analyze_image_with_text(result_url, question)

    # Update the interpretation_area with the interpretation text
    interpretation_area.object = interpretation_text


def submit_action(event):
    submit_button.disabled = True
    reset_button.disabled = True

    update_visualization(
        ticker_input.value,
        start_date.value,
        end_date.value,
        instruction_input.value,
        question.value,
    )

    submit_button.disabled = False
    reset_button.disabled = False


def reset_action(event):
    visualization_area.object = None
    interpretation_area.objetc = None


# Define the stock symbols you're interested in for the dropdown
stock_symbols, symbol_name = get_stock_symbols()
stat = ["Closing price", "Opening price", "Highest value of day", "Lowest value of day"]
stat_dic = {
    "Closing price": "Close",
    "Opening price": "Open",
    "Highest value of day": "High",
    "Lowest value of day": "Low",
}
# Create a header with the app's title and description
header = pn.pane.Markdown(
    """
## LLM-powered NASDAQ Stock Analysis App
""",
    margin=(0, 0, 10, 0),
    align="center",
)

description = pn.pane.Markdown(
    """
### How does it work?
This app analyzes stock data and provides visualizations and interpretations.
1. Select a stock symbol from the dropdown.
2. Select a start and end date for the analysis.
3. Select the value you want to analyze (e.g., closing price, opening price, etc.).
4. Enter a natural language question about the stock data.
The app will then display a plot of the selected stock's value over time and provide an interpretation of the plot generated by an LLM that takes into account the user's question.
""",
    margin=(0, 0, 10, 0),
)

# Add a logo at the top of the user menu
logo = pn.pane.PNG("image.png", width=200, height=100, align="center")

# Add credits at the bottom of the user menu
credits = pn.pane.Markdown(
    """
# How it was built
* Data source: yfinance
* Data storage: DuckDB
* UI: Panel
* Plotting: Plotly
* Plot Interpretation: OpenAI's gpt-4-vision-preview
""",
)


# UI Components for stock selection
# Define the AutocompleteInput for stock selection
ticker_input = pn.widgets.MultiChoice(
    name="Stock Symbol", options=stock_symbols, value=["AAPL", "GOOGL", "AMZN"]
)
start_date = pn.widgets.DatePicker(
    name="Start Date", value=date.today() - timedelta(days=7)
)
end_date = pn.widgets.DatePicker(name="End Date", value=date.today())
instruction_input = pn.widgets.Select(name="Value", options=stat, value="Close")
question = pn.widgets.TextAreaInput(
    name="Ask a natural language question",
    height=90,
    placeholder="What stock displays strongest growth over the selected period?",
    value="What stock displays strongest growth over the selected period?",
)

# Visualization area where the plot will be displayed
visualization_area = pn.pane.Plotly()
interpretation_area = pn.pane.Markdown("", width=600, styles={"font-size": "1.2em"})

submit_button = pn.widgets.Button(name="Submit", button_type="primary")
reset_button = pn.widgets.Button(name="Reset", button_type="danger")


submit_button.on_click(submit_action)
reset_button.on_click(reset_action)

# Organize the layout
user_menu = pn.Column(
    header,
    pn.pane.PNG("image.png", width=300, align="center"),
    description,
    ticker_input,
    start_date,
    end_date,
    instruction_input,
    question,
    submit_button,
    reset_button,
    credits,
    background="#F5F5F5",
    width=300,
    margin=(10, 10, 10, 10),
)

visualization_layout = pn.Column(
    "# Visualization",
    visualization_area,
    interpretation_area,
    background="#FFFFFF",
    margin=(10, 10, 10, 10),
)

# Combine the menu and visualization layout into the main layout
main_layout = pn.Row(user_menu, visualization_layout)

# Serve the app with a custom template that hides the theme toggle
template = pn.template.FastListTemplate(
    site="Ploomber Cloud",
    title="AI-powered Stock Analysis App",
    sidebar=[user_menu],
    accent="#DAA520",
    main=[visualization_layout],
    theme_toggle=False,
)

# Servable without the theme toggle
template.servable()
