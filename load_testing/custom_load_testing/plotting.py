import matplotlib.pyplot as plt
import seaborn as sns


def initialize_plot_grid(locustfile_list, users_list, is_ramped):
    """Initializes grid for visualizing all load-test results.

    Parameters
    ----------
    locustfile_list : list
        list of locustfiles tested
    users_list : list
        list of number of users tested
    is_ramped : bool
        whether the test was ramped or not

    Returns
    -------
    fig : matplotlib.figure.Figure
        figure object
    axes : numpy.ndarray
        array of axes objects

    """

    figsize_x = max(2.5 * len(users_list), 6)
    figsize_y = max(2.5 * len(locustfile_list), 6)

    f, axes = plt.subplots(
        len(locustfile_list) + is_ramped,
        len(users_list),
        squeeze=False,
        figsize=(figsize_x, figsize_y),
        sharex="col",
        sharey="row",
        constrained_layout=True,
    )
    f.supxlabel("Seconds Elapsed")

    return f, axes


def plot_test_stats_vs_time(
    test_stats_history,
    ys,
    labels,
    ax,
    locustfile_id,
    locustfile_no_ext,
    users_id,
    users,
):
    """Plots a test stats vs time on a given subplot with correct labelling.

    Parameters
    ----------
    test_stats_history : pandas.DataFrame
        dataframe containing test stats
    ys : list of str
        list of column names of test stat to plot as y-axis
    labels : list of str
        list of labels for plot legend
    ax : matplotlib.axes._subplots.AxesSubplot
        subplot to plot on
    locustfile_id : int
        index of locustfile in locustfile_list
    locustfile_no_ext : str
        name of locustfile without extension
    users_id : int
        index of number of users in users_list
    users : int
        number of users

    """
    for y, label in zip(ys, labels):
        sns.lineplot(
            data=test_stats_history,
            x="Seconds Elapsed",
            y=y,
            label=label,
            legend=None,
            ax=ax,
        )

    # remove x-axis label
    ax.set_xlabel("")
    # add number of users as title if subplot is in top row.
    if locustfile_id == 0:
        ax.set_title(f"{users} users")
    # add locustfile name as y-axis label if subplot is in first column.
    if users_id == 0:
        ax.set_ylabel(locustfile_no_ext)
    else:
        ax.set_ylabel("")
    # only add legend if subplot is the top left plot.
    if locustfile_id == 0 and users_id == 0:
        ax.legend(loc="upper left")


def plot_user_count(test_stats_history, ax):
    """Plots the number of users vs time on a given subplot."""
    sns.lineplot(
        data=test_stats_history,
        x="Seconds Elapsed",
        y="User Count",
        label="Total Users",
        legend=None,
        ax=ax,
    )
    ax.set_xlabel("")


def plot_results_vs_users(final_test_results, y, filename, output_folder):
    """Plots stats vs n_users for each locustfile used and saves plot to file.

    Parameters
    ----------
    final_test_results : pandas.DataFrame
        Results dataframe from collate_and_plot_all_results ######################################
    y : str
        Column to use as y-axis
    filename : str
        Name of file to save plot to

    """
    # Plot y vs number of users, colored by locustfile
    f, axes = plt.subplots(2, 1, figsize=(6, 6), constrained_layout=True)
    sns.lineplot(
        data=final_test_results,
        x="User Count",
        y=y,
        hue="locustfile",
        ax=axes[0],
    )
    # zoomed-in plot
    sns.lineplot(
        data=final_test_results[final_test_results["User Count"] <= 100],
        x="User Count",
        y=y,
        hue="locustfile",
        legend=None,
        ax=axes[1],
    )
    axes[1].set_title("Zoomed-in to first 100 users")
    plt.savefig(f"{output_folder}/processed/{filename}", dpi=300)
