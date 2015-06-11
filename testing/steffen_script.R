#!/usr/bin/Rscript

## Define what to do
OPTIMISEIPO <- TRUE
#OPTIMISEIPO <- FALSE

nSlaves <- 16

# Prepend EBI Metabolights User library 
.libPaths( c( "/nfs/public/rw/homes/tc_cm01/metabolights/software/R/x86_64-redhat-linux-gnu-library/3.1", .libPaths() ))

# Load libraries
library(Risa)
library(xcms)
library(IPO)
library(mzR) 

# Debug output
args <- commandArgs(trailingOnly = TRUE)
directory <- args[1]
#directory <- "/ebi/ftp/pub/databases/metabolights/studies/public/MTBLS2"
#directory <- "/vol/metabolights/public/MTBLS2"
accession <- basename(directory)

resultsprefix <- "/net/isilonP/public/rw/homes/tc_cm01/massIPO/results/"
outdir <- paste(resultsprefix, accession, sep="/")

cat(directory, "\n")
cat(outdir, "\n")


# Load ISAtab
isa <- readISAtab(directory)

for (assayfilename in isa["assay.filenames"]) {
  msfiles <- NULL
  i <- which(isa["assay.filenames"] == assayfilename)
  
  if (isa@assay.technology.types[i] != "mass spectrometry") {
    ## We don't care about non-MS assays
    next
  }
  
  if (Risa:::isatab.syntax$raw.spectral.data.file %in% colnames(isa["data.filenames"][[i]])) {
    msfiles = isa["data.filenames"][[i]][[Risa:::isatab.syntax$raw.spectral.data.file]]
  } else {
    ## No well annotated data files
    next
  }
  
  ## Get more information out of the ISA
  instrumentFromInvestigationFile <- as.character(isa@investigation.file[isa@investigation.file[,1] == "Study Assay Technology 
                                                                         Platform", 1+i])
  
  instrumentcolumn <- na.omit(match (c('Parameter Value[instrument]', 'Parameter Value[Instrument]'), 
                                     table=colnames(isa@assay.tabs[[i]]@assay.file)))
  
  instrumentFromAssayFile <- isa@assay.tabs[[i]]@assay.file[, instrumentcolumn[1]]
  
  ## Create output directory
  dir.create(outdir, showWarnings = FALSE)
  
  ## Obtain absolute file paths
  msfiles <- paste(directory, msfiles, sep="/")
  
  ## For now just use a subset of files:
  idx <- sample(length(msfiles), min(length(msfiles), 4))
  
  msfiles <- msfiles[idx]
  instrumentFromAssayFile <- instrumentFromAssayFile[idx]
  instrumentFromInvestigationFile <- t(t(rep(instrumentFromInvestigationFile, length(idx))))
  colnames(instrumentFromInvestigationFile) <- "instrumentFromInvestigationFile"
  
  ## Get some instrument info if available
  runinfo <- do.call(rbind, lapply(msfiles, function(msfile) {
    ms <- openMSfile(msfile)
    runInfo <- t(sapply(runInfo(ms), function(x) x[1], USE.NAMES=TRUE))
    instrumentInfo <- t(sapply(instrumentInfo(ms), function(x) x, USE.NAMES=TRUE))
    close(ms)
    cbind(runInfo, instrumentInfo)
  }))
  runinfo <- cbind(runinfo, instrumentFromAssayFile, instrumentFromInvestigationFile)
  
  if (OPTIMISEIPO) {    ## Optimise centWave
    peakpickingParameters <- getDefaultXcmsSetStartingParams('centWave')
    iporesult <- optimizeXcmsSet(files=msfiles,
                                 params=peakpickingParameters, 
                                 nSlaves=nSlaves,
                                 subdir=outdir)
    
    ## Write information to file
    parameters <- t(sapply(iporesult$best_settings$parameters, function(x) x[1]))
  } else {
    parameters <- t(t(rep("dummyparameters", length(msfiles))))
  }
  write.csv(cbind(msfiles, parameters),
            file=paste(outdir, "/", assayfilename, "-ipoparameters.csv", sep=""))
  
  write.csv(cbind(msfiles, runinfo),
            file=paste(outdir, "/", assayfilename, "-runinfo.csv", sep=""))
  
}



