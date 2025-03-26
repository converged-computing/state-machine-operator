import os

import matplotlib.pylab as plt
import seaborn as sns

timestamp_format = "%Y-%m-%dT%H:%M:%SZ"
node_timestamp_format = "%Y-%m-%dT%H:%M:%S.%fZ"


def make_plot(
    df,
    title,
    ydimension,
    xdimension,
    xlabel,
    ylabel,
    palette=None,
    ext="pdf",
    plotname="lammps",
    plot_type="violin",
    hue=None,
    outdir="img",
    do_log=False,
    ylim=None,
    rotation=90,
    width=7,
    height=6,
    order=None,
    remove_legend=False,
    remove_y=False,
    remove_x=False,
    xmin=None,
    xmax=None,
    ymin=None,
    ymax=None,
):
    """
    Helper function to make common plots.
    """
    plotfunc = sns.lineplot
    if plot_type == "violin":
        plotfunc = sns.violinplot
    elif plot_type == "box":
        plotfunc = sns.boxplot
    elif plot_type == "bar":
        plotfunc = sns.barplot

    ext = ext.strip(".")
    plt.figure(figsize=(width, height))
    sns.set_style("dark")
    if plot_type == "violin":
        ax = plotfunc(
            x=xdimension,
            y=ydimension,
            hue=hue,
            data=df,
            linewidth=0.8,
            palette=palette,
            marker="o",
        )
    elif plot_type == "bar":
        ax = plotfunc(
            x=xdimension,
            y=ydimension,
            hue=hue,
            data=df,
            linewidth=0.8,
            palette=palette,
            order=order,
        )
    elif plot_type == "box":
        ax = plotfunc(
            x=xdimension,
            y=ydimension,
            hue=hue,
            data=df,
            linewidth=1.8,
            order=order,
            palette=palette,
            whis=[5, 95],
            dodge=True,
        )
    else:
        ax = plotfunc(
            x=xdimension,
            y=ydimension,
            hue=hue,
            data=df,
            linewidth=1.8,
            palette=palette,
            # whis=[5, 95],
            # dodge=True,
        )
        # This range is specifically for pulling times -
        # so the ranges are equivalent
        if ylim is not None:
            ax.set(ylim=ylim)

    if do_log:
        plt.yscale("log")
    if remove_legend:
        ax.get_legend().set_title(None)
    if xmin is not None and xmax is not None:
        plt.xlim(xmin, xmax)
    if ymin is not None and ymax is not None:
        plt.ylim(ymin, ymax)
    plt.title(title)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize=14)
    ax.set_yticklabels(ax.get_yticks(), fontsize=14)
    # sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
    if remove_x:
        ax.set_xlabel(None)
    if remove_y:
        ax.set_ylabel(None)
        ax.set_yticks([])
    plt.xticks(rotation=rotation)
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{plotname}.svg"))
    plt.savefig(os.path.join(outdir, f"{plotname}.png"))
    plt.clf()
    return ax
