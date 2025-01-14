#!/bin/bash


cat fancyAdmixture_plot.R.template | sed "s/replacest/$1/g" | sed "s/replaceen/$2/g" | sed "s/replaceprefix/$3/g" > fancyAdmixture_plot.R
R CMD BATCH fancyAdmixture_plot.R
