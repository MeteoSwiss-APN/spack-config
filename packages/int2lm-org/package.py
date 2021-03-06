# Copyright 2013-2020 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

# ----------------------------------------------------------------------------
# If you submit this package back to Spack as a pull request,
from spack import *

import os
import subprocess

class Int2lmOrg(MakefilePackage):
    """INT2LM performs the interpolation from coarse grid model data to initial
    and/or boundary data for the COSMO-Model."""

    homepage = "http://www.cosmo-model.org/content/model/"
    url      = "https://github.com/COSMO-ORG/int2lm/archive/int2lm-2.07.tar.gz"
    git      = 'git@github.com:COSMO-ORG/int2lm.git'

    maintainers = ['egermann']

    version('master', branch='master')
    version('dev-build', branch='master')
    version('2.07', commit='65ddb3af9b7d63fa2019d8bcee41e8d4a99baedd')
    version('2.06a', commit='eb067a01446f55e1b55f6341681e97a95f856865')
    version('2.06', commit='11065ff1b304129ae19e774ebde02dcd743d2005')
    version('2.05', commit='ef16f54f53401e99aef083c447b4909b8230a4a0')

    depends_on('cosmo-grib-api-definitions', type=('build','run'), when='~eccodes')
    depends_on('cosmo-eccodes-definitions ~aec', type=('build','run'), when='+eccodes')
    depends_on('libgrib1@master')
    depends_on('mpi', type=('build', 'link', 'run'), when='+parallel')
    depends_on('netcdf-c')
    depends_on('netcdf-fortran +mpi')

    variant('debug', default=False, description='Build debug INT2LM')
    variant('eccodes', default=True, description='Build with eccodes instead of grib-api')
    variant('parallel', default=True, description='Build parallel INT2LM')
    variant('pollen', default=False, description='Build with pollen enabled')
    variant('slave', default='tsa', description='Build on slave tsa, daint or kesch', multi=False)
    variant('verbose', default=False, description='Build with verbose enabled')

    build_directory='TESTSUITE'

    def setup_build_environment(self, env):
        self.setup_run_environment(env)

        # Grib-api. Eccodes libraries
        if '~eccodes' in self.spec:
            grib_prefix = self.spec['cosmo-grib-api'].prefix
            grib_lib_names = '-lgrib_api_f90 -lgrib_api'
        else:
            grib_prefix = self.spec['eccodes'].prefix
            grib_lib_names = '-leccodes_f90 -leccodes'
        env.set('GRIBAPIL', '-L' + grib_prefix + '/lib ' + grib_lib_names + ' -L' + self.spec['jasper'].prefix + '/lib64 -ljasper')
        env.set('GRIBAPII', '-I' + grib_prefix + '/include')

        # Netcdf library
        if self.spec.variants['slave'].value == 'daint':
            env.set('NETCDFL', '-L$(NETCDF_DIR)/lib -lnetcdff -lnetcdf')
            env.set('NETCDFI', '-I$(NETCDF_DIR)/include')
        else:
            env.set('NETCDFL', '-L' + self.spec['netcdf-fortran'].prefix + '/lib -lnetcdff -L' + self.spec['netcdf-c'].prefix + '/lib64 -lnetcdf')
            env.set('NETCDFI', '-I' + self.spec['netcdf-fortran'].prefix + '/include')

        # Grib1 library
        if self.compiler.name == 'gcc':
            env.set('GRIBDWDL', '-L' + self.spec['libgrib1'].prefix + '/lib -lgrib1_gnu')
        elif self.compiler.name == 'cce':
            env.set('GRIBDWDL', '-L' + self.spec['libgrib1'].prefix + '/lib -lgrib1_cray')
        else:
            env.set('GRIBDWDL', '-L' + self.spec['libgrib1'].prefix + '/lib -lgrib1_' + self.compiler.name)

        # MPI library
        if self.spec['mpi'].name == 'openmpi':
            env.set('MPIL', '-L' + self.spec['mpi'].prefix + ' -lmpi_mpifh')
            env.set('MPII', '-I'+ self.spec['mpi'].prefix + '/include')
        else:
            env.set('MPII', '-I'+ self.spec['mpi'].prefix + '/include')
            if self.compiler.name != 'gcc':
                env.set('MPIL', '-L' + self.spec['mpi'].prefix + ' -lmpich_' + self.compiler.name)

        # Compiler & linker variables
        if self.compiler.name == 'pgi':
            env.set('F90', 'pgf90 -D__PGI_FORTRAN__')
            env.set('LD', 'pgf90 -D__PGI_FORTRAN__')
        elif self.compiler.name == 'cce':
            env.set('F90', 'ftn -D__CRAY_FORTRAN__')
            env.set('LD', 'ftn -D__CRAY_FORTRAN__')
        else:
            env.set('F90', self.spec['mpi'].mpifc)
            env.set('LD', self.spec['mpi'].mpifc)

    @property
    def build_targets(self):
        build = []
        if self.spec.variants['verbose'].value:
            build.append('VERBOSE=1')
        if self.spec.variants['pollen'].value:
            build.append('ART=1')
        MakeFileTarget = ''
        if '+parallel' in self.spec:
            MakeFileTarget += 'par'
        else:
            MakeFileTarget += 'seq'
        if '+debug' in self.spec:
            MakeFileTarget += 'debug'
        else:
            MakeFileTarget += 'opt'
        build.append(MakeFileTarget)

        return build

    def edit(self, spec, prefix):
        with working_dir(self.build_directory):
            makefile = FileFilter('Makefile')
            OptionsFileName= 'Options'
            if self.compiler.name == 'gcc':
                OptionsFileName += '.gnu'
            elif self.compiler.name == 'pgi':
                OptionsFileName += '.pgi'
            elif self.compiler.name == 'cce':
                OptionsFileName += '.cray'
            makefile.filter('/Options.*', '/' + OptionsFileName)

    def install(self, spec, prefix):
        with working_dir(self.build_directory):
            install('int2lm', prefix.bin)
            install('int2lm', '../test/testsuite')

    @run_after('install')
    @on_package_attributes(run_tests=True)
    def test(self):
        with working_dir('test/testsuite'):
            try:
                subprocess.run(['./test_int2lm.py', str(self.spec)], stderr=subprocess.STDOUT, check=True)
            except:
                raise InstallError('Testsuite failed')
