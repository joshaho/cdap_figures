#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import textwrap
import os
import zipfile

def polar_chart(dataframe, name="default_polar"):
    categories = dataframe.index.values
    categories = [*categories, categories[0]]

    target = dataframe["Target"].values*100
    company = dataframe["Your Score"].values*100
    company = [*company, company[0]]
    target = [*target, target[0]]
    label_loc = np.linspace(start=0, stop=2 * np.pi, num=len(company))

    plt.figure(figsize=(8, 8))
    plt.subplot(polar=True)
    plt.plot(label_loc, company, label='Current', color = '#005C80')
    plt.plot(label_loc, target, label='Target', color = '#35A080')
    #plt.plot(label_loc, restaurant_3, label='Restaurant 3')
#    plt.title('Recommendations', size=20, y=1.05)
    lines, labels = plt.thetagrids(np.degrees(label_loc), labels=categories)
    plt.fill_between(label_loc, company, 0, color = '#00A5E4')
    plt.fill_between(label_loc, company, target, color = '#7FD8BE')
#    plt.legend()
    st.write(name + " Generated.")
    plt.savefig('figures/'+name+'.png', format='png', bbox_inches='tight')
    plt.close()
    return

def prioritization_plot(dataframe):
    dataframe.plot(kind='scatter',x='Feasibility',y='Value', s='Effort_Scaled',color='#00ABEB')
    plt.axvline(x = 3, color = '#707070', label = 'axvline - full height')
    plt.axhline(y = 3, color = '#707070', label = 'axvline - full height')
    for i, txt in enumerate(dataframe.index):
        plt.annotate(txt.replace("[Enabler] ", ""), (dataframe.Feasibility[i], dataframe.Value[i]), fontsize=8)
    plt.xlim(0.8, 5.2)
    plt.ylim(0.8, 5.2)
    plt.savefig('figures/Prioritization.png', format='png', bbox_inches='tight', dpi=300)
    st.write("Prioritization Generated.")
    plt.close()
    return

def benchmark_plots(answers):
    for category in answers["Operational Indicators"].unique():
        plot_frame = answers[answers["Operational Indicators"]==category]
        plot_frame['Difference']= plot_frame['Target'] - plot_frame['Your Score']
        plt.figure(figsize=(6, 7), dpi=300)

        # Reorder it following the values of the first value:
        my_range=range(1,len(plot_frame.index)+1)
        spline_range = np.arange(0.5, len(plot_frame.index)+1.5)
        labels = plot_frame["Question"]
        if category == "Strategy":
            labels = [ '\n'.join(textwrap.wrap(l, 65)) for l in labels ]
            font = {
                'weight' : 'normal',
                'size'   : 14}
        else:
            labels = [ '\n'.join(textwrap.wrap(l, 45)) for l in labels ]
            font = {
                'weight' : 'normal',
                'size'   : 16}

        plt.rc('font', **font)
        i=0
        for i in range(len(plot_frame)):
            arrow_frame = plot_frame.reset_index(drop=True)
            if arrow_frame['Difference'].loc[i]>0:
                if plot_frame['Benchmark'].count() <= 1:
                    plt.arrow(arrow_frame['Your Score'].loc[i]+0.075, i+1, arrow_frame['Difference'].loc[i]-0.2, 0, head_width = 0.015, facecolor = 'black')
                else:
                    plt.arrow(arrow_frame['Your Score'].loc[i]+0.075, i+1, arrow_frame['Difference'].loc[i]-0.3, 0, head_width = 0.075, facecolor = 'black')
            i+=1
        plt.scatter(plot_frame['Target'], my_range, color='green', s=200, alpha=0.6 , label='Target State')
        plt.scatter(plot_frame['Your Score'], my_range, color='skyblue', s=50, alpha=0.6, label='Your Score', marker='D')

        if plot_frame['Benchmark'].count() <= 1:
            spline_frame = pd.concat([plot_frame, plot_frame])
        else:

            spline_frame = pd.concat([plot_frame, plot_frame.iloc[[-1]]])
        plt.step(spline_frame['Benchmark'], spline_range, color='grey', alpha=0.6 , label='Benchmark')

        # Add title and axis names
        plt.yticks(my_range, labels)
        plt.xlim([0, 5])
        plt.xlabel('Score')
        plt.savefig('figures/benchmark_'+category+'.png', format='png', bbox_inches='tight')
        plt.close()

    st.write("Benchmark Plots Generated.")
    return

def zipdir(path, ziph):
            # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            if ".png" in file:
                ziph.write(os.path.join(root, file),
                             os.path.relpath(os.path.join(root, file),
                                             os.path.join(path, '..')))

def process_figure_generation(): #Create File

    uploaded_file = st.file_uploader("Upload Files", type = ['xlsx'])
    if uploaded_file is not None:
        file_details = {"FileName":uploaded_file.name, "FileType":uploaded_file.type, "FileSize":uploaded_file.size}
        st.write(file_details)

        #Read in the right sheets
        datafile = pd.ExcelFile(uploaded_file, engine="openpyxl")
        answers = pd.read_excel(datafile, sheet_name="CDAP Data", index_col="Index")
        mapping = pd.read_excel(datafile, sheet_name="Technology Suggestions", index_col="Index")
        prioritization = pd.read_excel(datafile, sheet_name="Technology Prioritization", index_col="Technology")


        #Manipulate Dataframe to right format
        mapping_long = mapping.drop("Question", axis=1).melt(ignore_index=False)
        mapping_filtered = mapping_long[mapping_long.value =="Yes"]
        full_dataset = answers.join(mapping_filtered)
        score_summary = full_dataset.groupby(by = "variable").sum().drop("Benchmark", axis=1)
        normalized_score_summary=(score_summary)/(score_summary.max().max())
        normalized_score_summary["Need Score"] = normalized_score_summary["Target"] - normalized_score_summary["Your Score"]
        enabler_summary = normalized_score_summary.filter(like="[Enabler]", axis=0)
        enabler_summary.index=(enabler_summary.index.str.split(']')).str[1]
        technologies_summary = normalized_score_summary.drop(normalized_score_summary.filter(like="[Enabler]", axis=0).index)

        joined_prioritization_frame = prioritization.join(normalized_score_summary)
        joined_prioritization_frame["Value"]=1+4*(joined_prioritization_frame["Need Score"]/joined_prioritization_frame["Need Score"].max())
        joined_prioritization_frame["Effort_Scaled"] = joined_prioritization_frame["Effort"]*80

        #Generate Charts
        polar_chart(enabler_summary, 'Enablers')
        polar_chart(technologies_summary, 'Technologies')
        prioritization_plot(joined_prioritization_frame)
        benchmark_plots(answers)

        with zipfile.ZipFile('figures/images.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipdir('figures/', zipf)
    else:
        file_path = "./CDAP Template.xlsx"
        with open(file_path, 'rb') as my_file:
            st.download_button(label = 'Download Blank Template', data = my_file, file_name = 'CDAP Template.xlsx', mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')





def main():
    st.title("CDAP Graph Generation")
    if not os.path.exists('figures'):
        os.makedirs('figures')
    process_figure_generation()
    if os.path.exists('figures/images.zip'):
        with open('figures/images.zip', 'rb') as f:
            clear_cache = st.download_button('Download Zip', f, on_click=True, file_name='archive.zip')  # Defaults to 'application/octet-stream'
            if clear_cache:
                for root, dirs, files in os.walk('figures/'):
                    for file in files:
                        os.remove(file)

if __name__ == "__main__":
    main()
